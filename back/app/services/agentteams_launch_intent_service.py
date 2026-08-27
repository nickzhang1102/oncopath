"""Durable AgentTeams launch orchestration and reconciliation."""

import hashlib
import json
import logging
import uuid
from datetime import timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, text, true, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agentteams_launch_intent import (
    AgentTeamsLaunchIntent,
    AgentTeamsLaunchIntentAudit,
)
from app.models.conversation import Conversation, ConsultationExternalSession
from app.models.notification import Notification
from app.models.patient import Patient
from app.models.user import LoginAccount
from app.schemas.agentteams import (
    AgentTeamsLaunchIntentResponse,
    AgentTeamsStartRequest,
)
from app.services.agentteams_config_service import AgentTeamsConfigService
from app.services.agentteams_start_service import AgentTeamsStartService
from app.services.consultation.medical_prompt_builder import MedicalPromptBuilder
from app.services.conversation_service import ConversationService
from app.services.encryption_service import encryption_service
from app.services.patient_service import PatientService
from app.utils.time_utils import get_utc_now


logger = logging.getLogger(__name__)


class AgentTeamsLaunchIntentService:
    """Own the local launch state; AgentTeams only owns the remote execution."""

    PROVIDER = "agentteams"
    ACTIVE_INTENT_STATUSES = {
        "prepared",
        "dispatching",
        "confirming",
        "manual_review",
    }
    REMOTE_TERMINAL_STATUSES = {"completed", "failed", "stopped"}
    REMOTE_FAILURE_STATUSES = {"failed", "stopped"}
    DEFINITE_REJECTION_STATUSES = {400, 401, 402, 403, 409, 422, 426}
    STALE_DISPATCH_SECONDS = 45
    DISPATCH_LEASE_SECONDS = 90
    RECONCILE_LEASE_SECONDS = 45
    RECONCILE_BACKOFF_SECONDS = (2, 5, 15, 30, 60, 300)
    MAX_RECONCILE_ATTEMPTS = 8

    def __init__(self, db: AsyncSession):
        self.db = db
        self.agentteams = AgentTeamsStartService(db)

    async def start(
        self,
        data: AgentTeamsStartRequest,
        account_id: int,
    ) -> AgentTeamsLaunchIntentResponse:
        if data.conversation_id is not None:
            response = await self.agentteams.start(data, account_id)
            return AgentTeamsLaunchIntentResponse(
                request_id=data.request_id,
                conversation_id=response.conversation_id,
                patient_id=data.patient_id,
                launch_status="accepted",
                external_conversation_id=response.external_conversation_id,
                external_session_id=response.external_session_id,
                external_share_token=response.external_share_token,
                embed_url=response.embed_url,
                status=response.status,
            )

        if data.request_id is None:
            raise HTTPException(status_code=422, detail="request_id is required")

        config = await AgentTeamsConfigService(self.db).get_runtime_config()
        if not config.configured or not config.enabled:
            raise HTTPException(
                status_code=503,
                detail={"error": "agentteams_not_configured", "message": "AgentTeams 未配置或未启用"},
            )
        await PatientService.verify_ownership(self.db, data.patient_id, account_id)
        await self._lock_patient(account_id, data.patient_id)

        request_id = str(data.request_id)
        intent = await self._get_by_request_id(request_id, account_id, data.patient_id)
        if intent is None:
            intent = await self._get_active_patient_intent(account_id, data.patient_id)
        if intent is None:
            intent = await self._create_intent(data, account_id)

        if intent.status == "prepared":
            await self.dispatch(intent.id)
        elif intent.status in {"dispatching", "confirming"}:
            # A deliberate user request can perform one immediate read-only
            # reconciliation; the background worker still obeys backoff.
            await self.reconcile(intent.id, force=True)

        await self.db.refresh(intent)
        if intent.status == "rejected":
            raise self._rejection_error(intent)
        return await self._to_response(intent)

    async def get_active(
        self,
        account_id: int,
        patient_id: int,
    ) -> AgentTeamsLaunchIntentResponse | None:
        await PatientService.verify_ownership(self.db, patient_id, account_id)
        intent = await self._get_active_patient_intent(account_id, patient_id)
        if intent is None:
            return None
        if intent.status in {"dispatching", "confirming"}:
            await self.reconcile(intent.id)
            await self.db.refresh(intent)
        return await self._to_response(intent)

    async def _lock_patient(self, account_id: int, patient_id: int) -> None:
        lock_key = (int(account_id) << 32) ^ int(patient_id)
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": lock_key},
        )

    async def _create_intent(
        self,
        data: AgentTeamsStartRequest,
        account_id: int,
    ) -> AgentTeamsLaunchIntent:
        conversation = await ConversationService(self.db).create_conversation(
            user_id=account_id,
            patient_id=data.patient_id,
            title="待生成会诊标题",
        )
        prompt_config = await self.agentteams._load_prompt_config(data.patient_id, account_id)
        prompt = await MedicalPromptBuilder().build_consultation_prompt(
            patient_id=data.patient_id,
            db=self.db,
            prompt_config=prompt_config,
        )
        if not prompt.strip():
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail={"error": "launch_failed", "message": "无法生成会诊提示词"},
            )

        conversation.title = self.agentteams._build_conversation_title(prompt, conversation)
        conversation.status = "analyzing"
        payload = {
            "user_ref": f"oncopath:{account_id}",
            "subject_ref": str(data.patient_id),
            "conversation_ref": str(conversation.id),
            "title": conversation.title,
            "message": prompt,
            "locale": self.agentteams.CLIENT_LOCALE,
            "metadata": {"created_from": "oncopath"},
        }
        canonical_payload = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        intent = AgentTeamsLaunchIntent(
            provider=self.PROVIDER,
            request_id=str(data.request_id),
            conversation_id=conversation.id,
            account_id=account_id,
            patient_id=data.patient_id,
            status="prepared",
            payload_ciphertext=encryption_service.encrypt(canonical_payload),
            payload_hash=hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest(),
        )
        self.db.add(intent)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            winner = await self._get_by_request_id(
                str(data.request_id), account_id, data.patient_id
            )
            if winner is None:
                winner = await self._get_active_patient_intent(account_id, data.patient_id)
            if winner is None:
                # request_id is globally unique per provider.  A request key
                # belonging to another account/patient must be a safe 409,
                # never an unhandled integrity error/500.
                existing = await self._get_any_by_request_id(str(data.request_id))
                if existing is not None:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "error": "agentteams_idempotency_conflict",
                            "message": "该启动标识已用于其他会诊，请重新发起",
                        },
                    )
                raise
            return winner
        await self.db.refresh(intent)
        return intent

    async def dispatch(self, intent_id: int) -> None:
        now = get_utc_now()
        lease_owner = uuid.uuid4().hex
        claimed = await self.db.execute(
            update(AgentTeamsLaunchIntent)
            .where(
                AgentTeamsLaunchIntent.id == intent_id,
                AgentTeamsLaunchIntent.status == "prepared",
                (
                    AgentTeamsLaunchIntent.lease_expires_at.is_(None)
                    | (AgentTeamsLaunchIntent.lease_expires_at <= now)
                ),
            )
            .values(
                status="dispatching",
                dispatch_started_at=now,
                lease_owner=lease_owner,
                lease_expires_at=now + timedelta(seconds=self.DISPATCH_LEASE_SECONDS),
                next_attempt_at=None,
                attempt_count=AgentTeamsLaunchIntent.attempt_count + 1,
                last_error_status=None,
                last_error_code=None,
                last_error_message=None,
            )
        )
        await self.db.commit()
        if claimed.rowcount != 1:
            return
        intent = await self.db.get(AgentTeamsLaunchIntent, intent_id)
        if intent is None:
            return

        config = await AgentTeamsConfigService(self.db).get_runtime_config()
        try:
            payload = self._decrypt_payload(intent)
            result = await self.agentteams._call_agentteams_launch(
                base_url=config.base_url,
                integration_secret=config.integration_secret,
                request_id=self.agentteams._build_remote_request_id(
                    intent.request_id, intent.conversation_id
                ),
                payload=payload,
            )
        except HTTPException as exc:
            intent = await self._get_owned_intent(intent_id, lease_owner)
            if intent is None:
                return
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            intent.status = (
                "rejected"
                if exc.status_code in self.DEFINITE_REJECTION_STATUSES
                else "confirming"
            )
            intent.last_error_status = exc.status_code
            intent.last_error_code = str(detail.get("error") or "agentteams_unavailable")
            intent.last_error_message = str(detail.get("message") or "")
            if intent.status == "rejected":
                await self._mark_conversation_rejected(intent)
                self._purge_terminal_payload(intent)
            else:
                await self._defer_reconciliation(intent)
            if intent.status == "rejected":
                intent.lease_owner = None
                intent.lease_expires_at = None
            await self.db.commit()
            return
        except Exception as exc:
            intent = await self._get_owned_intent(intent_id, lease_owner)
            if intent is None:
                return
            logger.exception("AgentTeams durable dispatch failed: intent_id=%s", intent.id)
            intent.status = "confirming"
            intent.last_error_status = 502
            intent.last_error_code = "agentteams_unavailable"
            intent.last_error_message = str(exc)[:500]
            await self._defer_reconciliation(intent)
            await self.db.commit()
            return

        await self._accept(intent, result, config.base_url, lease_owner=lease_owner)

    async def reconcile(
        self,
        intent_id: int,
        force: bool = False,
        allow_manual_review: bool = False,
    ) -> bool:
        now = get_utc_now()
        stale_before = now - timedelta(seconds=self.STALE_DISPATCH_SECONDS)
        lease_owner = uuid.uuid4().hex
        eligible_statuses = {"dispatching", "confirming"}
        if allow_manual_review:
            eligible_statuses.add("manual_review")
        claimed = await self.db.execute(
            update(AgentTeamsLaunchIntent)
            .where(
                AgentTeamsLaunchIntent.id == intent_id,
                AgentTeamsLaunchIntent.status.in_(eligible_statuses),
                (
                    AgentTeamsLaunchIntent.lease_expires_at.is_(None)
                    | (AgentTeamsLaunchIntent.lease_expires_at <= now)
                ),
                true()
                if force
                else (
                    AgentTeamsLaunchIntent.next_attempt_at.is_(None)
                    | (AgentTeamsLaunchIntent.next_attempt_at <= now)
                ),
                (
                    AgentTeamsLaunchIntent.status.in_({"confirming", "manual_review"})
                    | AgentTeamsLaunchIntent.dispatch_started_at.is_(None)
                    | (AgentTeamsLaunchIntent.dispatch_started_at <= stale_before)
                ),
            )
            .values(
                lease_owner=lease_owner,
                lease_expires_at=now + timedelta(seconds=self.RECONCILE_LEASE_SECONDS),
                attempt_count=AgentTeamsLaunchIntent.attempt_count + 1,
            )
        )
        await self.db.commit()
        if claimed.rowcount != 1:
            return False
        intent = await self.db.get(AgentTeamsLaunchIntent, intent_id)
        if intent is None:
            return False

        config = await AgentTeamsConfigService(self.db).get_runtime_config()
        try:
            result = await self.agentteams._call_agentteams_launch_status(
                base_url=config.base_url,
                integration_secret=config.integration_secret,
                request_id=self.agentteams._build_remote_request_id(
                    intent.request_id, intent.conversation_id
                ),
            )
        except HTTPException as exc:
            intent = await self._get_owned_intent(intent_id, lease_owner)
            if intent is None:
                return False
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            intent.status = "confirming"
            intent.last_error_status = exc.status_code
            intent.last_error_code = str(detail.get("error") or "agentteams_unavailable")
            intent.last_error_message = str(detail.get("message") or "")
            await self._defer_reconciliation(intent)
            await self.db.commit()
            return True

        if not result.get("found"):
            # A timed-out POST may still be committing remotely.  A single
            # read that cannot see the row is therefore not proof that the
            # launch never happened.  Keep performing bounded, read-only
            # reconciliation; never open the door to a second chargeable POST
            # on the strength of one transient not-found result.
            intent = await self._get_owned_intent(intent_id, lease_owner)
            if intent is None:
                return False
            intent.status = "confirming"
            intent.last_error_status = 404
            intent.last_error_code = "agentteams_launch_not_found"
            intent.last_error_message = "AgentTeams 暂未查询到该会诊，继续确认启动结果"
            await self._defer_reconciliation(intent)
            await self.db.commit()
            return True

        # status 查询是对账的权威依据；已失败/已停止的远程工作流是终态，
        # 绝不能把其转换为一个新的嵌入令牌。
        remote_status = str(result.get("status") or "").strip().lower()
        if remote_status in self.REMOTE_FAILURE_STATUSES:
            intent = await self._get_owned_intent(intent_id, lease_owner)
            if intent is None:
                return False
            intent.status = "rejected"
            intent.last_error_status = 409
            intent.last_error_code = str(
                result.get("error_code") or f"agentteams_launch_{remote_status}"
            )
            intent.last_error_message = (
                "AgentTeams 会诊已停止"
                if remote_status == "stopped"
                else "AgentTeams 会诊启动失败"
            )
            intent.lease_owner = None
            intent.lease_expires_at = None
            self._purge_terminal_payload(intent)
            await self._mark_conversation_rejected(intent)
            await self.db.commit()
            return True

        # 嵌入令牌仅在原始 launch 响应中铸造；status 响应无法找回遗失的令牌，
        # 因此到此止步进入人工复核，而不是隐式续期或循环重试。
        if not intent.embed_url:
            intent = await self._get_owned_intent(intent_id, lease_owner)
            if intent is None:
                return False
            intent.status = "manual_review"
            intent.last_error_status = 502
            intent.last_error_code = "agentteams_embed_unavailable"
            intent.last_error_message = "AgentTeams 未返回初始嵌入地址"
            intent.next_attempt_at = None
            intent.lease_owner = None
            intent.lease_expires_at = None
            await self.db.commit()
            return True
        return await self._accept(intent, result, config.base_url, lease_owner=lease_owner)

    async def admin_reconcile_manual_review(
        self,
        intent_id: int,
        actor_account_id: int,
    ) -> AgentTeamsLaunchIntent:
        intent = await self.db.get(AgentTeamsLaunchIntent, intent_id)
        if intent is None:
            raise HTTPException(status_code=404, detail="启动意图不存在")
        if intent.status != "manual_review":
            raise HTTPException(status_code=409, detail="启动意图不在人工复核状态")

        before_status = intent.status
        claimed = await self.reconcile(
            intent_id,
            force=True,
            allow_manual_review=True,
        )
        intent = await self.db.get(AgentTeamsLaunchIntent, intent_id)
        if intent is None:
            raise HTTPException(status_code=404, detail="启动意图不存在")
        if not claimed:
            await self.db.refresh(intent)
            now = get_utc_now()
            if (
                intent.status == "manual_review"
                and intent.lease_owner
                and intent.lease_expires_at is not None
                and intent.lease_expires_at > now
            ):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "agentteams_reconcile_in_progress",
                        "message": "该启动意图正在对账，请等待对账完成后再重试",
                    },
                )
            raise HTTPException(status_code=409, detail="启动意图已被其他操作更新")
        await self.db.refresh(intent)
        self.db.add(
            AgentTeamsLaunchIntentAudit(
                intent_id=intent.id,
                request_id=intent.request_id,
                actor_account_id=actor_account_id,
                action="read_only_reconcile",
                before_status=before_status,
                after_status=intent.status,
                error_code=intent.last_error_code,
            )
        )
        await self.db.commit()
        await self.db.refresh(intent)
        return intent

    async def admin_confirm_not_created(
        self,
        intent_id: int,
        actor_account_id: int,
        reason: str,
    ) -> AgentTeamsLaunchIntent:
        result = await self.db.execute(
            select(AgentTeamsLaunchIntent)
            .where(AgentTeamsLaunchIntent.id == intent_id)
            .with_for_update()
        )
        intent = result.scalar_one_or_none()
        if intent is None:
            raise HTTPException(status_code=404, detail="启动意图不存在")
        if intent.status != "manual_review":
            raise HTTPException(status_code=409, detail="启动意图不在人工复核状态")
        now = get_utc_now()
        if (
            intent.lease_owner
            and intent.lease_expires_at is not None
            and intent.lease_expires_at > now
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "agentteams_reconcile_in_progress",
                    "message": "该启动意图正在对账，请等待对账完成后再处置",
                },
            )

        before_status = intent.status
        intent.status = "rejected"
        intent.last_error_status = 409
        intent.last_error_code = "agentteams_manually_confirmed_not_created"
        intent.last_error_message = "管理员已在 AgentTeams 外部核验该启动未创建"
        intent.next_attempt_at = None
        intent.lease_owner = None
        intent.lease_expires_at = None
        self._purge_terminal_payload(intent)
        await self._mark_conversation_rejected(intent)
        self.db.add(
            AgentTeamsLaunchIntentAudit(
                intent_id=intent.id,
                request_id=intent.request_id,
                actor_account_id=actor_account_id,
                action="confirmed_not_created",
                before_status=before_status,
                after_status=intent.status,
                reason=reason.strip(),
                error_code=intent.last_error_code,
            )
        )
        await self.db.commit()
        await self.db.refresh(intent)
        return intent

    async def process_available(self, limit: int = 20) -> int:
        """Process a bounded batch for the durable worker."""
        result = await self.db.execute(
            select(AgentTeamsLaunchIntent.id)
            .where(
                AgentTeamsLaunchIntent.status.in_(
                    {"prepared", "dispatching", "confirming"}
                ),
                (
                    AgentTeamsLaunchIntent.lease_expires_at.is_(None)
                    | (AgentTeamsLaunchIntent.lease_expires_at <= get_utc_now())
                ),
                (
                    AgentTeamsLaunchIntent.next_attempt_at.is_(None)
                    | (AgentTeamsLaunchIntent.next_attempt_at <= get_utc_now())
                ),
            )
            .order_by(AgentTeamsLaunchIntent.created_at.asc())
            .limit(limit)
        )
        intent_ids = list(result.scalars())
        for intent_id in intent_ids:
            intent = await self.db.get(AgentTeamsLaunchIntent, intent_id)
            if intent is None:
                continue
            if intent.status == "prepared":
                await self.dispatch(intent_id)
            else:
                await self.reconcile(intent_id)
        return len(intent_ids)

    async def _accept(
        self,
        intent: AgentTeamsLaunchIntent,
        result: dict[str, Any],
        base_url: str,
        lease_owner: str | None = None,
    ) -> bool:
        if lease_owner is not None:
            owned_intent = await self._get_owned_intent(intent.id, lease_owner)
            if owned_intent is None:
                # 当前由人工处置或更新的 worker 持有该意图，
            # 绝不能让这份迟到的远端响应覆盖该决定。
                return False
            intent = owned_intent
        embed_path = result.get("embed_path")
        external_conversation_id = result.get("agentteams_conversation_id")
        if not embed_path and intent.embed_url:
            # 只读对账复用原始 launch 铸造的地址；绝不可铸造替代品。
            embed_path = intent.embed_url
            base_url = ""
        if not embed_path or external_conversation_id in (None, ""):
            intent.last_error_status = 502
            intent.last_error_code = "agentteams_unavailable"
            intent.last_error_message = "AgentTeams 返回字段不完整"
            await self._defer_reconciliation(intent)
            await self.db.commit()
            return True

        intent.external_conversation_id = str(external_conversation_id)
        if result.get("agentteams_session_id") is not None:
            intent.external_session_id = self.agentteams._optional_str(
                result.get("agentteams_session_id")
            )
        if result.get("agentteams_share_token") is not None:
            intent.external_share_token = self.agentteams._optional_str(
                result.get("agentteams_share_token")
            )
        if base_url:
            intent.embed_url = self.agentteams._build_embed_url(base_url, str(embed_path))
        intent.remote_status = str(result.get("status") or "created")
        intent.status = "accepted"
        intent.last_error_code = None
        intent.last_error_message = None
        intent.last_error_status = None
        intent.lease_owner = None
        intent.lease_expires_at = None
        intent.next_attempt_at = None
        self._purge_terminal_payload(intent)

        intent_id = intent.id
        loser_conversation_id = intent.conversation_id
        intent_request_id = intent.request_id
        intent_account_id = intent.account_id
        intent_patient_id = intent.patient_id
        mapping = await self._get_mapping(intent.conversation_id)
        if mapping is None:
            mapping = ConsultationExternalSession(
                conversation_id=intent.conversation_id,
                provider=self.PROVIDER,
                launch_request_id=intent.request_id,
                external_conversation_id=intent.external_conversation_id,
                external_session_id=intent.external_session_id,
                external_share_token=intent.external_share_token,
                embed_url=intent.embed_url,
                status=intent.remote_status,
            )
            self.db.add(mapping)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            winner = await self.agentteams._get_external_session_by_request_id(
                intent_request_id,
                intent_account_id,
                intent_patient_id,
            )
            if winner is None:
                raise
            intent = await self.db.get(AgentTeamsLaunchIntent, intent_id)
            loser = await self.db.get(Conversation, loser_conversation_id)
            if intent is None:
                raise
            intent.conversation_id = winner.conversation_id
            intent.status = "accepted"
            intent.external_conversation_id = winner.external_conversation_id
            intent.external_session_id = winner.external_session_id
            intent.external_share_token = winner.external_share_token
            intent.embed_url = winner.embed_url
            intent.remote_status = winner.status
            intent.last_error_code = None
            intent.last_error_message = None
            intent.last_error_status = None
            intent.lease_owner = None
            intent.lease_expires_at = None
            intent.next_attempt_at = None
            self._purge_terminal_payload(intent)
            await self.db.flush()
            if loser is not None and loser.id != winner.conversation_id:
                await self.db.delete(loser)
            await self.db.commit()
        return True

    async def _get_owned_intent(
        self,
        intent_id: int,
        lease_owner: str,
    ) -> AgentTeamsLaunchIntent | None:
        """Reload a lease holder and lock it before applying a remote result.

        The lease is the compare-and-set guard for the network gap between a
        claim and its final write.  Expired owners are stale and must not be
        allowed to overwrite a manual decision or a newer worker's result.
        """
        result = await self.db.execute(
            select(AgentTeamsLaunchIntent)
            .where(
                AgentTeamsLaunchIntent.id == intent_id,
                AgentTeamsLaunchIntent.lease_owner == lease_owner,
                AgentTeamsLaunchIntent.lease_expires_at > get_utc_now(),
            )
            .with_for_update()
        )
        intent = result.scalar_one_or_none()
        if intent is None:
            await self.db.rollback()
        return intent

    async def _defer_reconciliation(self, intent: AgentTeamsLaunchIntent) -> None:
        """Release a lease with bounded backoff; stop infinite polling."""
        if intent.attempt_count >= self.MAX_RECONCILE_ATTEMPTS:
            intent.status = "manual_review"
            intent.last_error_code = "agentteams_reconciliation_exhausted"
            intent.last_error_message = "AgentTeams 启动结果多次无法确认，请人工核对"
            intent.next_attempt_at = None
            await self._mark_conversation_rejected(intent)
            await self._notify_admins_manual_review(intent)
        else:
            intent.status = "confirming"
            intent.next_attempt_at = get_utc_now() + timedelta(
                seconds=self._backoff_seconds(intent.attempt_count)
            )
        intent.lease_owner = None
        intent.lease_expires_at = None

    async def _notify_admins_manual_review(self, intent: AgentTeamsLaunchIntent) -> None:
        """进入人工复核时为全体 active 管理员写入通知。

        仅 db.add 挂入当前事务、随外层 commit 原子落库（不独立 commit/publish）；
        任何失败只记日志，绝不阻断启动状态机。该分支对同一 intent 仅触发一次
        （worker 路径不再认领 manual_review 状态），无需额外去重。
        """
        try:
            result = await self.db.execute(
                select(LoginAccount.account_id).where(
                    LoginAccount.account_type == "admin",
                    LoginAccount.status == "active",
                )
            )
            for account_id in result.scalars().all():
                self.db.add(Notification(
                    account_id=account_id,
                    type="consultation",
                    title="会诊启动需人工复核",
                    content=(
                        f"会诊对话 #{intent.conversation_id} 启动结果多次自动确认失败，"
                        "已转入人工复核，请前往管理后台「会诊启动复核」处置。"
                    ),
                    extra_data={
                        "intent_id": intent.id,
                        "conversation_id": intent.conversation_id,
                        "request_id": intent.request_id,
                        "error_code": intent.last_error_code,
                    },
                ))
        except Exception as exc:
            logger.warning(
                "写入人工复核管理员通知失败 (intent_id=%s): %s", intent.id, exc
            )

    @staticmethod
    def _purge_terminal_payload(intent: AgentTeamsLaunchIntent) -> None:
        """Drop the encrypted medical prompt once the launch is terminal."""
        if intent.payload_ciphertext is not None:
            intent.payload_ciphertext = None
            intent.payload_purged_at = get_utc_now()

    @classmethod
    def _backoff_seconds(cls, attempt_count: int | None) -> int:
        index = max(int(attempt_count or 1) - 1, 0)
        return cls.RECONCILE_BACKOFF_SECONDS[
            min(index, len(cls.RECONCILE_BACKOFF_SECONDS) - 1)
        ]

    async def _get_by_request_id(
        self,
        request_id: str,
        account_id: int,
        patient_id: int,
    ) -> AgentTeamsLaunchIntent | None:
        result = await self.db.execute(
            select(AgentTeamsLaunchIntent).where(
                AgentTeamsLaunchIntent.provider == self.PROVIDER,
                AgentTeamsLaunchIntent.request_id == request_id,
                AgentTeamsLaunchIntent.account_id == account_id,
                AgentTeamsLaunchIntent.patient_id == patient_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_any_by_request_id(
        self,
        request_id: str,
    ) -> AgentTeamsLaunchIntent | None:
        result = await self.db.execute(
            select(AgentTeamsLaunchIntent).where(
                AgentTeamsLaunchIntent.provider == self.PROVIDER,
                AgentTeamsLaunchIntent.request_id == request_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_mapping(
        self,
        conversation_id: int,
    ) -> ConsultationExternalSession | None:
        result = await self.db.execute(
            select(ConsultationExternalSession).where(
                ConsultationExternalSession.conversation_id == conversation_id,
                ConsultationExternalSession.provider == self.PROVIDER,
            )
        )
        return result.scalar_one_or_none()

    async def _get_active_patient_intent(
        self,
        account_id: int,
        patient_id: int,
    ) -> AgentTeamsLaunchIntent | None:
        # ``accepted`` is the terminal state of the *launch* state machine.
        # It must not be used as a patient-level launch lock: a completed
        # embed callback is not guaranteed when a user closes the page, and
        # treating an accepted/running mapping as unresolved can route a new
        # request UUID back to an old consultation forever.  Runtime
        # concurrency, if product policy requires it, belongs to a separate
        # authoritative execution-status policy rather than launch intent.
        result = await self.db.execute(
            select(AgentTeamsLaunchIntent)
            .where(
                AgentTeamsLaunchIntent.provider == self.PROVIDER,
                AgentTeamsLaunchIntent.account_id == account_id,
                AgentTeamsLaunchIntent.patient_id == patient_id,
                AgentTeamsLaunchIntent.status.in_(self.ACTIVE_INTENT_STATUSES),
            )
            .order_by(AgentTeamsLaunchIntent.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _mark_conversation_rejected(
        self,
        intent: AgentTeamsLaunchIntent,
    ) -> None:
        conversation = await self.db.get(Conversation, intent.conversation_id)
        if conversation is not None:
            conversation.status = "error"

    @staticmethod
    def _rejection_error(intent: AgentTeamsLaunchIntent) -> HTTPException:
        status_code = int(intent.last_error_status or 409)
        # Never expose an arbitrary provider status as a FastAPI response;
        # terminal statuses are deliberately constrained to the integration
        # contract's safe range.
        if status_code < 400 or status_code >= 500:
            status_code = 409
        return HTTPException(
            status_code=status_code,
            detail={
                "error": intent.last_error_code or "agentteams_rejected",
                "message": intent.last_error_message or "AgentTeams 拒绝启动会诊",
            },
        )

    def _decrypt_payload(self, intent: AgentTeamsLaunchIntent) -> dict[str, Any]:
        plaintext = encryption_service.decrypt(intent.payload_ciphertext)
        if not plaintext:
            raise RuntimeError("AgentTeams launch payload is missing")
        if hashlib.sha256(plaintext.encode("utf-8")).hexdigest() != intent.payload_hash:
            raise RuntimeError("AgentTeams launch payload integrity check failed")
        return json.loads(plaintext)

    async def _to_response(
        self,
        intent: AgentTeamsLaunchIntent,
    ) -> AgentTeamsLaunchIntentResponse:
        mapping = await self._get_mapping(intent.conversation_id)
        return AgentTeamsLaunchIntentResponse(
            request_id=intent.request_id,
            conversation_id=intent.conversation_id,
            patient_id=intent.patient_id,
            launch_status=intent.status,
            external_conversation_id=(
                mapping.external_conversation_id if mapping else intent.external_conversation_id
            ),
            external_session_id=(
                mapping.external_session_id if mapping else intent.external_session_id
            ),
            external_share_token=(
                mapping.external_share_token if mapping else intent.external_share_token
            ),
            embed_url=mapping.embed_url if mapping else intent.embed_url,
            status=mapping.status if mapping else (intent.remote_status or intent.status),
            error=intent.last_error_code,
        )
