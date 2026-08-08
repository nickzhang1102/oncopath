"""AgentTeams 会诊启动服务"""

import logging
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import Conversation, ConsultationExternalSession
from app.models.patient import Patient
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
    REQUEST_TIMEOUT_SECONDS = 20.0

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
        conversation = await self._resolve_conversation(data, account_id)
        existing_mapping = await self.get_external_session(conversation.id, account_id, raise_not_found=False)
        if existing_mapping:
            renewed_mapping = await self.get_external_session(conversation.id, account_id, raise_not_found=True)
            return AgentTeamsStartResponse(**renewed_mapping.model_dump())

        prompt = await MedicalPromptBuilder().build_consultation_prompt(
            patient_id=data.patient_id,
            db=self.db,
        )
        if not prompt.strip():
            raise HTTPException(
                status_code=500,
                detail={"error": "launch_failed", "message": "无法生成会诊提示词"},
            )

        conversation.status = "analyzing"
        await self.db.flush()

        request_id = f"oncopath-conversation-{conversation.id}"
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
                    "title": conversation.title or "虚拟会诊",
                    "message": prompt,
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
            external_conversation_id=str(launch_result["agentteams_conversation_id"]),
            external_session_id=self._optional_str(launch_result.get("agentteams_session_id")),
            external_share_token=self._optional_str(launch_result.get("agentteams_share_token")),
            embed_url=self._build_embed_url(config.base_url, str(launch_result["embed_path"])),
            status=str(launch_result.get("status") or "created"),
        )
        self.db.add(mapping)
        await self.db.commit()
        await self.db.refresh(mapping)
        return self._to_response(mapping)

    async def get_external_session(
        self,
        conversation_id: int,
        account_id: int,
        patient_id: int | None = None,
        raise_not_found: bool = True,
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
        if raise_not_found:
            await self._renew_embed_url(mapping)
        return self._to_response(mapping)

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
        mapping.status = str(renew_result.get("status") or mapping.status or "created")
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(mapping)

    async def _resolve_conversation(self, data: AgentTeamsStartRequest, account_id: int) -> Conversation:
        service = ConversationService(self.db)
        if data.conversation_id:
            conversation = await service.get_conversation_by_id(data.conversation_id)
            if not conversation or conversation.user_id != account_id or conversation.patient_id != data.patient_id:
                raise HTTPException(status_code=404, detail="会诊记录不存在或无权访问")
            return conversation

        return await service.create_conversation(
            user_id=account_id,
            patient_id=data.patient_id,
            title="虚拟会诊",
        )

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
