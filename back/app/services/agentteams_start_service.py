"""AgentTeams 会诊启动服务"""

import logging
import re
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import Conversation, ConsultationExternalSession
from app.models.patient import Patient
from app.models.prompt import PromptConfig
from app.schemas.agentteams import (
    AgentTeamsExternalSessionResponse,
    AgentTeamsStartRequest,
    AgentTeamsStartResponse,
)
from app.services.agentteams_config_service import AgentTeamsConfigService
from app.services.consultation.medical_prompt_builder import MedicalPromptBuilder
from app.services.conversation_service import ConversationService
from app.services.patient_service import PatientService

logger = logging.getLogger(__name__)


class AgentTeamsStartService:
    """编排 OncoPath 到 AgentTeams 的外部会诊启动。"""

    PROVIDER = "agentteams"
    CLIENT_LOCALE = "zh-CN"
    REQUEST_TIMEOUT_SECONDS = 20.0
    MAX_TITLE_LENGTH = 32
    TITLE_SUMMARY_LENGTH = 10
    GENERIC_TITLES = {"", "待生成会诊标题", "虚拟会诊", "AgentTeams 会诊"}
    TERMINAL_STATUSES = {"completed", "failed", "stopped"}

    def __init__(self, db: AsyncSession):
        self.db = db

    async def start(
        self,
        data: AgentTeamsStartRequest,
        account_id: int,
    ) -> AgentTeamsStartResponse:
        config = await AgentTeamsConfigService(self.db).get_runtime_config()
        if not config.configured or not config.enabled:
            raise HTTPException(
                status_code=503,
                detail={"error": "agentteams_not_configured", "message": "AgentTeams 未配置或未启用"},
            )

        await PatientService.verify_ownership(self.db, data.patient_id, account_id)
        if data.request_id is not None:
            existing_request_mapping = await self._get_external_session_by_request_id(
                str(data.request_id), account_id, data.patient_id
            )
            if existing_request_mapping is not None:
                if (
                    data.conversation_id is not None
                    and existing_request_mapping.conversation_id != data.conversation_id
                ):
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "error": "agentteams_idempotency_conflict",
                            "message": "启动标识与会诊记录不匹配，请重新发起",
                        },
                    )
                await self._renew_embed_url(existing_request_mapping)
                return AgentTeamsStartResponse(**self._to_response(existing_request_mapping).model_dump())
        conversation = await self._resolve_conversation(data, account_id)
        existing_mapping = await self.get_external_session(conversation.id, account_id, raise_not_found=False)
        if (
            existing_mapping is not None
            and data.request_id is not None
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "agentteams_idempotency_conflict",
                    "message": "启动标识与会诊记录不匹配，请重新发起",
                },
            )
        if existing_mapping and not self._needs_title_refresh(conversation.title):
            renewed_mapping = await self.get_external_session(
                conversation.id,
                account_id,
                raise_not_found=True,
                renew_embed=True,
            )
            return AgentTeamsStartResponse(**renewed_mapping.model_dump())

        prompt_config = await self._load_prompt_config(data.patient_id, account_id)
        prompt = await MedicalPromptBuilder().build_consultation_prompt(
            patient_id=data.patient_id,
            db=self.db,
            prompt_config=prompt_config,
        )
        if not prompt.strip():
            raise HTTPException(
                status_code=500,
                detail={"error": "launch_failed", "message": "无法生成会诊提示词"},
            )

        if self._needs_title_refresh(conversation.title):
            conversation.title = self._build_conversation_title(prompt, conversation)
            await self.db.flush()

        if existing_mapping:
            renewed_mapping = await self.get_external_session(
                conversation.id,
                account_id,
                raise_not_found=True,
                renew_embed=True,
            )
            return AgentTeamsStartResponse(**renewed_mapping.model_dump())

        logger.info(
            "AgentTeams launch prompt prepared: conversation_id=%s patient_id=%s "
            "prompt_config_id=%s prompt_chars=%s",
            conversation.id,
            data.patient_id,
            prompt_config.get("config_id") if prompt_config else None,
            len(prompt),
        )

        conversation.status = "analyzing"
        await self.db.flush()

        launch_request_id = str(data.request_id) if data.request_id is not None else None
        request_id = self._build_remote_request_id(launch_request_id, conversation.id)
        try:
            launch_result = await self._call_agentteams_launch(
                base_url=config.base_url,
                integration_secret=config.integration_secret,
                request_id=request_id,
                payload={
                    "source": "oncopath",
                    "source_user_id": f"oncopath:{account_id}",
                    "source_patient_id": str(data.patient_id),
                    "source_conversation_id": conversation.id,
                    "title": conversation.title,
                    "message": prompt,
                    "locale": self.CLIENT_LOCALE,
                    "metadata": {"created_from": "oncopath"},
                },
            )
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as exc:
            logger.error("AgentTeams launch failed: conversation_id=%s error=%s", conversation.id, exc)
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail={"error": "launch_failed", "message": "启动 AgentTeams 会诊失败"},
            ) from exc

        mapping = ConsultationExternalSession(
            conversation_id=conversation.id,
            provider=self.PROVIDER,
            launch_request_id=launch_request_id,
            external_conversation_id=str(launch_result["agentteams_conversation_id"]),
            external_session_id=self._optional_str(launch_result.get("agentteams_session_id")),
            external_share_token=self._optional_str(launch_result.get("agentteams_share_token")),
            embed_url=self._build_embed_url(config.base_url, str(launch_result["embed_path"])),
            status=str(launch_result.get("status") or "created"),
        )
        self.db.add(mapping)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            if launch_request_id is not None:
                winner = await self._get_external_session_by_request_id(
                    launch_request_id,
                    account_id,
                    data.patient_id,
                )
                if winner is not None:
                    logger.info(
                        "AgentTeams launch converged to concurrent winner: request_id=%s conversation_id=%s",
                        launch_request_id,
                        winner.conversation_id,
                    )
                    return AgentTeamsStartResponse(**self._to_response(winner).model_dump())
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "agentteams_idempotency_conflict",
                        "message": "该启动标识已用于其他会诊，请重新发起",
                    },
                ) from exc
            raise
        await self.db.refresh(mapping)
        return self._to_response(mapping)

    async def _load_prompt_config(self, patient_id: int, account_id: int) -> dict[str, Any] | None:
        """Load the same saved configuration used by the prompt preview page."""
        result = await self.db.execute(
            select(PromptConfig)
            .where(PromptConfig.patient_id == patient_id)
            .order_by(
                PromptConfig.updated_at.desc().nullslast(),
                PromptConfig.config_id.desc(),
            )
            .limit(1)
        )
        config = result.scalar_one_or_none()
        if config is None:
            return None
        if config.account_id != account_id:
            # PromptConfig has historically been read and updated by patient_id.
            # Keep launch behavior aligned with that patient-owned contract so
            # legacy rows do not silently fall back to the short default prompt.
            logger.warning(
                "Using legacy patient-owned prompt config with stale account_id: "
                "patient_id=%s config_id=%s config_account_id=%s owner_account_id=%s",
                patient_id,
                config.config_id,
                config.account_id,
                account_id,
            )
        return config.to_dict()

    async def get_external_session(
        self,
        conversation_id: int,
        account_id: int,
        patient_id: int | None = None,
        raise_not_found: bool = True,
        renew_embed: bool = False,
    ) -> AgentTeamsExternalSessionResponse | None:
        filters = [
            ConsultationExternalSession.conversation_id == conversation_id,
            ConsultationExternalSession.provider == self.PROVIDER,
            Conversation.user_id == account_id,
        ]
        stmt = select(ConsultationExternalSession).join(
            Conversation, Conversation.id == ConsultationExternalSession.conversation_id
        )
        if patient_id is not None:
            # 按患者隔离：校验会诊归属该患者，且患者归属当前账号
            filters.extend([
                Conversation.patient_id == patient_id,
                Patient.account_id == account_id,
            ])
            stmt = stmt.join(Patient, Patient.patient_id == Conversation.patient_id)
        result = await self.db.execute(stmt.where(*filters))
        mapping = result.scalar_one_or_none()
        if not mapping:
            if raise_not_found:
                raise HTTPException(status_code=404, detail="外部会诊映射不存在")
            return None
        if renew_embed:
            await self._renew_embed_url(mapping)
        return self._to_response(mapping)

    async def _get_external_session_by_request_id(
        self,
        request_id: str,
        account_id: int,
        patient_id: int,
    ) -> ConsultationExternalSession | None:
        result = await self.db.execute(
            select(ConsultationExternalSession)
            .join(Conversation, Conversation.id == ConsultationExternalSession.conversation_id)
            .where(
                ConsultationExternalSession.provider == self.PROVIDER,
                ConsultationExternalSession.launch_request_id == request_id,
                Conversation.user_id == account_id,
                Conversation.patient_id == patient_id,
            )
        )
        return result.scalar_one_or_none()

    async def _renew_embed_url(self, mapping: ConsultationExternalSession) -> None:
        config = await AgentTeamsConfigService(self.db).get_runtime_config()
        if not config.configured or not config.enabled:
            raise HTTPException(
                status_code=503,
                detail={"error": "agentteams_not_configured", "message": "AgentTeams 未配置或未启用"},
            )

        try:
            renew_result = await self._call_agentteams_embed_renew(
                base_url=config.base_url,
                integration_secret=config.integration_secret,
                payload={
                    "source_conversation_id": mapping.conversation_id,
                    "request_id": self._build_remote_request_id(
                        mapping.launch_request_id, mapping.conversation_id
                    ) if mapping.launch_request_id else None,
                    "agentteams_conversation_id": self._optional_int(mapping.external_conversation_id),
                    "agentteams_session_id": self._optional_int(mapping.external_session_id),
                },
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("AgentTeams embed renew failed: conversation_id=%s error=%s", mapping.conversation_id, exc)
            raise HTTPException(
                status_code=502,
                detail={"error": "agentteams_unavailable", "message": "AgentTeams 服务暂时不可用"},
            ) from exc

        embed_path = renew_result.get("embed_path")
        if not embed_path:
            raise HTTPException(
                status_code=502,
                detail={"error": "agentteams_unavailable", "message": "AgentTeams 返回字段不完整"},
            )

        mapping.embed_url = self._build_embed_url(config.base_url, str(embed_path))
        mapping.status = self._merge_external_status(
            mapping.status,
            renew_result.get("status"),
        )
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(mapping)

    async def update_external_status(
        self,
        conversation_id: int,
        account_id: int,
        patient_id: int,
        status: str,
    ) -> AgentTeamsExternalSessionResponse:
        stmt = (
            select(ConsultationExternalSession)
            .join(Conversation, Conversation.id == ConsultationExternalSession.conversation_id)
            .join(Patient, Patient.patient_id == Conversation.patient_id)
            .where(
                ConsultationExternalSession.conversation_id == conversation_id,
                ConsultationExternalSession.provider == self.PROVIDER,
                Conversation.user_id == account_id,
                Conversation.patient_id == patient_id,
                Patient.account_id == account_id,
            )
        )
        result = await self.db.execute(stmt)
        mapping = result.scalar_one_or_none()
        if mapping is None:
            raise HTTPException(status_code=404, detail="外部会诊映射不存在")

        mapping.status = self._merge_external_status(mapping.status, status)
        await self.db.commit()
        await self.db.refresh(mapping)
        return self._to_response(mapping)

    async def _resolve_conversation(
        self,
        data: AgentTeamsStartRequest,
        account_id: int,
    ) -> Conversation:
        service = ConversationService(self.db)
        if data.conversation_id:
            conversation = await service.get_conversation_by_id(data.conversation_id)
            if not conversation or conversation.user_id != account_id or conversation.patient_id != data.patient_id:
                raise HTTPException(status_code=404, detail="会诊记录不存在或无权访问")
            return conversation

        conversation = await service.create_conversation(
            user_id=account_id,
            patient_id=data.patient_id,
            title="待生成会诊标题",
        )
        return conversation

    @classmethod
    def _is_generic_title(cls, title: str | None) -> bool:
        return (title or "").strip() in cls.GENERIC_TITLES

    @classmethod
    def _needs_title_refresh(cls, title: str | None) -> bool:
        normalized = (title or "").strip()
        # 兼容 2026-08-11 前使用的“患者标识 · 创建时间 · 会诊#编号”标题。
        return cls._is_generic_title(normalized) or bool(
            re.search(r"·\s*(?:会诊\s*)?#\d+", normalized)
        )

    @classmethod
    def _build_conversation_title(
        cls,
        prompt: str,
        conversation: Conversation,
    ) -> str:
        """从会诊提示词提取不超过 10 字的主题，再拼接稳定编号。"""
        summary = cls._summarize_prompt_title(prompt)
        suffix = f"-#{conversation.id}"
        summary_budget = max(cls.MAX_TITLE_LENGTH - len(suffix), 0)
        return f"{summary[:summary_budget]}{suffix}"

    @classmethod
    def _summarize_prompt_title(cls, prompt: str) -> str:
        raw_text = str(prompt or "").replace("\r", "")
        lines = [re.sub(r"\s+", " ", line).strip() for line in raw_text.split("\n")]
        lines = [line for line in lines if line]
        if not lines:
            return "病情分析"

        # 优先取诊断/病理/病史字段，避免标题落到“姓名、性别”等低信号内容。
        candidate = ""
        for line in lines:
            labeled = re.match(
                r"(?:病理诊断|诊断结果|诊断意见|诊断|癌种|肿瘤类型|病史)\s*[:：]\s*(.+)$",
                line,
            )
            if labeled:
                candidate = labeled.group(1)
                break
        if not candidate:
            candidate = lines[0].split("：", 1)[-1]

        candidate = re.sub(r"^[\s#：:：、，,。.!！?？]+|[\s#：:：、，,。.!！?？]+$", "", candidate)
        candidate = re.sub(r"(?:未填写|无|暂无|不详)$", "", candidate).strip()
        if not candidate:
            return "病情分析"

        # 过滤提示词里的模板指令，保留疾病主题；中文标题按字符数控制。
        candidate = re.sub(r"^(?:请根据以上信息|请提供|请给出|患者资料)\s*", "", candidate)
        candidate = re.sub(r"[\s，,、；;。.!！?？:：]+", "", candidate)
        if candidate.startswith(("gAAAA", "enc")):
            return "病情分析"

        # 中文主题统一保留固定语义后缀，主题总长度控制在 10 字内。
        if re.fullmatch(r"[\u3400-\u9fff]+", candidate):
            suffix = "病情分析"
            candidate = f"{candidate[: cls.TITLE_SUMMARY_LENGTH - len(suffix)]}{suffix}"
        candidate = candidate[: cls.TITLE_SUMMARY_LENGTH]
        return candidate or "病情分析"

    async def _call_agentteams_launch(
        self,
        base_url: str,
        integration_secret: str,
        request_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        url = f"{self._build_agentteams_api_base(base_url)}/api/integrations/oncopath/consultation-launches"
        headers = {
            "X-Integration-Key": integration_secret,
            "X-Request-Id": request_id,
        }
        try:
            async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload, headers=headers)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning("AgentTeams launch unavailable: request_id=%s error=%s", request_id, exc)
            raise HTTPException(
                status_code=502,
                detail={"error": "agentteams_unavailable", "message": "AgentTeams 服务暂时不可用"},
            ) from exc

        if response.status_code >= 400:
            self._raise_agentteams_error(response)

        try:
            result = response.json()
        except ValueError as exc:
            raise HTTPException(
                status_code=502,
                detail={"error": "agentteams_unavailable", "message": "AgentTeams 返回格式异常"},
            ) from exc

        required = {"agentteams_conversation_id", "embed_path"}
        if not required.issubset(result):
            raise HTTPException(
                status_code=502,
                detail={"error": "agentteams_unavailable", "message": "AgentTeams 返回字段不完整"},
            )
        return result

    async def _call_agentteams_embed_renew(
        self,
        base_url: str,
        integration_secret: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        url = f"{self._build_agentteams_api_base(base_url)}/api/integrations/oncopath/embed-sessions/renew"
        headers = {"X-Integration-Key": integration_secret}
        try:
            async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload, headers=headers)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning("AgentTeams embed renew unavailable: conversation_id=%s error=%s", payload.get("source_conversation_id"), exc)
            raise HTTPException(
                status_code=502,
                detail={"error": "agentteams_unavailable", "message": "AgentTeams 服务暂时不可用"},
            ) from exc

        if response.status_code >= 400:
            self._raise_agentteams_error(response)

        try:
            return response.json()
        except ValueError as exc:
            raise HTTPException(
                status_code=502,
                detail={"error": "agentteams_unavailable", "message": "AgentTeams 返回格式异常"},
            ) from exc

    def _build_agentteams_api_base(self, base_url: str) -> str:
        base = base_url.rstrip("/")
        if base.startswith("http://") or base.startswith("https://"):
            return base
        if base.startswith("/"):
            origin = settings.AGENTTEAMS_INTERNAL_ORIGIN.rstrip("/")
            if origin:
                return f"{origin}{base}"
        raise HTTPException(
            status_code=503,
            detail={"error": "agentteams_not_configured", "message": "AgentTeams 地址配置无效"},
        )

    @staticmethod
    def _build_embed_url(base_url: str, embed_path: str) -> str:
        base = base_url.rstrip("/")
        path = embed_path if embed_path.startswith("/") else f"/{embed_path}"
        return f"{base}{path}"

    @staticmethod
    def _build_remote_request_id(request_id: str | None, conversation_id: int) -> str:
        if request_id:
            return f"oncopath-launch-{request_id}"
        return f"oncopath-conversation-{conversation_id}"

    @staticmethod
    def _raise_agentteams_error(response: httpx.Response) -> None:
        error_code = ""
        try:
            body = response.json()
            detail = body.get("detail", {})
            if isinstance(detail, dict):
                error_code = str(detail.get("error") or "")
        except ValueError:
            error_code = ""

        mapping = {
            "invalid_integration_key": (502, "agentteams_invalid_integration_key", "AgentTeams 集成密钥无效"),
            "service_account_quota_exceeded": (402, "agentteams_quota_exceeded", "AgentTeams 会诊额度不足"),
            "service_account_not_configured": (403, "agentteams_service_account_not_configured", "AgentTeams 服务账户未配置"),
            "integration_disabled": (403, "agentteams_integration_disabled", "AgentTeams 集成未启用"),
            "unsupported_version": (426, "agentteams_unsupported_version", "AgentTeams 版本不兼容"),
            "idempotency_conflict": (409, "agentteams_idempotency_conflict", "该启动标识已用于其他会诊，请重新发起"),
        }
        status_code, mapped_error, message = mapping.get(
            error_code,
            (502, "agentteams_unavailable", "AgentTeams 服务暂时不可用"),
        )
        raise HTTPException(
            status_code=status_code,
            detail={"error": mapped_error, "message": message},
        )

    @staticmethod
    def _to_response(mapping: ConsultationExternalSession) -> AgentTeamsExternalSessionResponse:
        return AgentTeamsExternalSessionResponse(
            conversation_id=mapping.conversation_id,
            provider=mapping.provider,
            external_conversation_id=mapping.external_conversation_id,
            external_session_id=mapping.external_session_id,
            external_share_token=mapping.external_share_token,
            embed_url=mapping.embed_url,
            status=mapping.status,
        )

    @classmethod
    def _merge_external_status(cls, current: str | None, incoming: Any) -> str:
        current_status = str(current or "created")
        if current_status in cls.TERMINAL_STATUSES:
            return current_status
        return str(incoming or current_status)

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
