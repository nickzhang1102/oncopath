"""AgentTeams 管理后台配置 API"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_admin_user
from app.core.database import get_db
from app.models.user import LoginAccount
from app.models.agentteams_launch_intent import (
    AgentTeamsLaunchIntent,
    AgentTeamsLaunchIntentAudit,
)
from app.schemas.agentteams import (
    AgentTeamsConfigResponse,
    AgentTeamsConfigUpdate,
    AgentTeamsLaunchIntentAdminDetail,
    AgentTeamsLaunchIntentAdminItem,
    AgentTeamsLaunchIntentAuditItem,
    AgentTeamsManualReviewResolveRequest,
)
from app.services.agentteams_config_service import (
    AgentTeamsConfigError,
    AgentTeamsConfigService,
)
from app.services.agentteams_launch_intent_service import AgentTeamsLaunchIntentService

router = APIRouter()


def _intent_item(intent: AgentTeamsLaunchIntent) -> AgentTeamsLaunchIntentAdminItem:
    return AgentTeamsLaunchIntentAdminItem(
        id=intent.id,
        request_id=intent.request_id,
        conversation_id=intent.conversation_id,
        account_id=intent.account_id,
        patient_id=intent.patient_id,
        launch_status=intent.status,
        attempt_count=intent.attempt_count,
        remote_status=intent.remote_status,
        external_conversation_id=intent.external_conversation_id,
        external_session_id=intent.external_session_id,
        last_error_status=intent.last_error_status,
        last_error_code=intent.last_error_code,
        last_error_message=intent.last_error_message,
        payload_hash=intent.payload_hash,
        payload_retained=intent.payload_ciphertext is not None,
        payload_purged_at=intent.payload_purged_at,
        created_at=intent.created_at,
        updated_at=intent.updated_at,
    )


async def _intent_detail(
    db: AsyncSession,
    intent: AgentTeamsLaunchIntent,
) -> AgentTeamsLaunchIntentAdminDetail:
    audit_result = await db.execute(
        select(AgentTeamsLaunchIntentAudit)
        .where(AgentTeamsLaunchIntentAudit.intent_id == intent.id)
        .order_by(AgentTeamsLaunchIntentAudit.created_at.desc())
    )
    audits = [
        AgentTeamsLaunchIntentAuditItem(
            id=audit.id,
            actor_account_id=audit.actor_account_id,
            action=audit.action,
            before_status=audit.before_status,
            after_status=audit.after_status,
            reason=audit.reason,
            error_code=audit.error_code,
            created_at=audit.created_at,
        )
        for audit in audit_result.scalars().all()
    ]
    return AgentTeamsLaunchIntentAdminDetail(
        **_intent_item(intent).model_dump(),
        audits=audits,
    )


@router.get("/agentteams-config", response_model=AgentTeamsConfigResponse)
async def get_agentteams_config(
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = AgentTeamsConfigService(db)
    return await service.get_config()


@router.put("/agentteams-config", response_model=AgentTeamsConfigResponse)
async def update_agentteams_config(
    data: AgentTeamsConfigUpdate,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = AgentTeamsConfigService(db)
    try:
        return await service.update_config(data)
    except AgentTeamsConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/agentteams-launch-intents",
    response_model=list[AgentTeamsLaunchIntentAdminItem],
)
async def list_agentteams_launch_intents(
    launch_status: str = Query(default="manual_review", alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    allowed_statuses = {
        "prepared", "dispatching", "confirming", "accepted", "rejected", "manual_review"
    }
    if launch_status not in allowed_statuses:
        raise HTTPException(status_code=422, detail="无效的启动意图状态")
    result = await db.execute(
        select(AgentTeamsLaunchIntent)
        .where(AgentTeamsLaunchIntent.status == launch_status)
        .order_by(AgentTeamsLaunchIntent.updated_at.asc())
        .limit(limit)
    )
    return [_intent_item(intent) for intent in result.scalars().all()]


@router.get(
    "/agentteams-launch-intents/{intent_id}",
    response_model=AgentTeamsLaunchIntentAdminDetail,
)
async def get_agentteams_launch_intent(
    intent_id: int,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    intent = await db.get(AgentTeamsLaunchIntent, intent_id)
    if intent is None:
        raise HTTPException(status_code=404, detail="启动意图不存在")
    return await _intent_detail(db, intent)


@router.post(
    "/agentteams-launch-intents/{intent_id}/reconcile",
    response_model=AgentTeamsLaunchIntentAdminDetail,
)
async def reconcile_agentteams_launch_intent(
    intent_id: int,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    intent = await AgentTeamsLaunchIntentService(db).admin_reconcile_manual_review(
        intent_id,
        admin_user.account_id,
    )
    return await _intent_detail(db, intent)


@router.post(
    "/agentteams-launch-intents/{intent_id}/resolve",
    response_model=AgentTeamsLaunchIntentAdminDetail,
)
async def resolve_agentteams_launch_intent(
    intent_id: int,
    data: AgentTeamsManualReviewResolveRequest,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    intent = await AgentTeamsLaunchIntentService(db).admin_confirm_not_created(
        intent_id,
        admin_user.account_id,
        data.reason,
    )
    return await _intent_detail(db, intent)
