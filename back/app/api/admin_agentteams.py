"""AgentTeams 管理后台配置 API"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_admin_user
from app.core.database import get_db
from app.models.user import LoginAccount
from app.schemas.agentteams import AgentTeamsConfigResponse, AgentTeamsConfigUpdate
from app.services.agentteams_config_service import (
    AgentTeamsConfigError,
    AgentTeamsConfigService,
)

router = APIRouter()


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
