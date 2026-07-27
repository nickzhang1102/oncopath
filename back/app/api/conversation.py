"""AgentTeams consultation and legacy conversation compatibility routes.

Current endpoints:
- POST /consultation/conversations — 创建会诊对话
- GET  /consultation/conversations — 获取会诊列表
- DELETE /consultation/conversations/{id} — 删除会诊
- POST /consultation/conversations/{id}/share — 生成分享令牌
- POST /consultation/agentteams/start — 启动 AgentTeams 会诊
- POST /consultation/start 等旧本地执行端点 — 返回 410
- GET  /consultation/session/{conversation_id} — 获取会话数据
- GET  /consultation/session/share/{token} — 分享链接访问
- GET  /consultation/share/{token} — 分享链接访问（短路径）
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import LoginAccount
from app.schemas.conversation import (
    ConversationCreate, ConversationResponse, ConversationListResponse,
    StartLeaderSessionRequest, AnswerQuestionsRequest, AnswerQuestionsBody, StopSessionRequest,
    GenerateShareTokenRequest, GenerateShareTokenResponse,
    VerifySharePasswordRequest,
)
from app.schemas.agentteams import AgentTeamsAvailabilityResponse, AgentTeamsExternalSessionResponse
from app.schemas.agentteams import AgentTeamsStartRequest, AgentTeamsStartResponse
from app.services.agentteams_config_service import AgentTeamsConfigService
from app.services.agentteams_start_service import AgentTeamsStartService
from app.services.conversation_service import ConversationService

router = APIRouter()


def _raise_local_consultation_disabled() -> None:
    raise HTTPException(
        status_code=410,
        detail={
            "error": "local_consultation_disabled",
            "message": "本地虚拟会诊已下线，请使用 AgentTeams 会诊",
        },
    )


@router.get("/agentteams/availability", response_model=AgentTeamsAvailabilityResponse)
async def get_agentteams_availability(
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """查询 AgentTeams 集成可用性，不返回集成密钥。"""
    service = AgentTeamsConfigService(db)
    return await service.get_availability()


@router.post("/agentteams/start", response_model=AgentTeamsStartResponse)
async def start_agentteams_consultation(
    data: AgentTeamsStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """启动 AgentTeams 外部会诊并返回嵌入地址。"""
    service = AgentTeamsStartService(db)
    return await service.start(data, current_user.account_id)


@router.get("/agentteams/sessions/{conversation_id}", response_model=AgentTeamsExternalSessionResponse)
async def get_agentteams_external_session(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """读取本地会诊对应的 AgentTeams 外部会话映射。"""
    service = AgentTeamsStartService(db)
    return await service.get_external_session(conversation_id, current_user.account_id)


# ===== 会诊对话 CRUD =====

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """旧本地会诊壳创建入口已下线；请使用 AgentTeams start。"""
    _raise_local_consultation_disabled()


@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """获取会诊列表（我的会诊）"""
    service = ConversationService(db)
    conversations, total = await service.get_conversations(
        user_id=current_user.account_id, limit=limit, offset=offset
    )
    return ConversationListResponse(
        conversations=conversations, total=total, limit=limit, offset=offset
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """删除会诊对话"""
    service = ConversationService(db)
    deleted = await service.delete_conversation(conversation_id, current_user.account_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="对话不存在")
    await db.commit()
    return {"success": True}


# ===== Leader 会话管理 =====

@router.post("/start")
@limiter.limit("5/minute")
async def start_consultation(
    request: Request,
    data: StartLeaderSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """旧本地 Leader/SSE 会诊入口已下线。"""
    _raise_local_consultation_disabled()


@router.post("/stop")
async def stop_consultation(
    data: StopSessionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """旧本地 Leader 停止入口已下线。"""
    _raise_local_consultation_disabled()


@router.post("/session/{session_id}/stop")
async def stop_consultation_by_path(
    session_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """旧本地 Leader 停止入口已下线。"""
    _raise_local_consultation_disabled()


@router.post("/answer-questions")
async def answer_questions(
    data: AnswerQuestionsRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """旧本地 Leader 追问入口已下线。"""
    _raise_local_consultation_disabled()


@router.post("/session/{session_id}/answer")
async def answer_questions_by_path(
    session_id: int,
    data: AnswerQuestionsBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """旧本地 Leader 追问入口已下线。"""
    _raise_local_consultation_disabled()


@router.get("/session/{conversation_id}/stream")
async def reconnect_consultation_stream(
    conversation_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """旧本地 Leader/SSE 重连入口已下线。"""
    _raise_local_consultation_disabled()


@router.get("/session/{conversation_id}")
async def get_session_data(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """认证旧本地会诊详情入口已下线；详情页请使用 AgentTeams mapping。"""
    _raise_local_consultation_disabled()


@router.get("/session/share/{token}")
@limiter.limit("10/minute")
async def get_shared_session(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """通过分享令牌访问会话数据（无需认证）

    如果设置了分享密码，返回需要验证的提示；客户端需调用验证端点。
    """
    service = ConversationService(db)
    conversation = await service.get_conversation_by_token(token)
    if not conversation:
        raise HTTPException(status_code=404, detail="分享链接无效或已过期")

    # 校验过期时间
    from app.utils.time_utils import get_utc_now
    if conversation.share_expire_at and get_utc_now() > conversation.share_expire_at:
        raise HTTPException(status_code=410, detail="分享链接已过期")

    # 如果设置了密码，返回需要验证的提示
    if conversation.share_password:
        return {"requires_password": True, "has_password": True}

    # 无密码，直接返回数据
    data = await service.get_session_data(conversation.id)
    if not data:
        raise HTTPException(status_code=404, detail="分享链接无效或已过期")
    return data


@router.post("/conversations/{conversation_id}/share", response_model=GenerateShareTokenResponse)
async def generate_share_token(
    conversation_id: int,
    data: GenerateShareTokenRequest = GenerateShareTokenRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """生成会诊分享令牌

    支持设置分享密码和过期时间。如果对话已有 share_token 则更新密码/过期设置。
    """
    service = ConversationService(db)
    conversation = await service.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    # 验证用户权限
    if conversation.user_id != current_user.account_id:
        raise HTTPException(status_code=403, detail="无权操作此对话")

    # 生成新令牌并保存（含密码和过期设置）
    share_token, has_password, expire_at = await service.generate_and_save_share_token(
        conversation_id,
        password=data.password,
        expire_hours=data.expire_hours,
    )
    await db.commit()

    return GenerateShareTokenResponse(
        share_token=share_token,
        share_url=f"/share/{share_token}",
        has_password=has_password,
        expire_at=expire_at,
    )


@router.get("/share/{share_token}")
@limiter.limit("10/minute")
async def get_shared_session_short(
    request: Request,
    share_token: str,
    db: AsyncSession = Depends(get_db),
):
    """通过分享令牌访问会话数据（短路径，无需认证）

    与 /session/share/{token} 功能相同，提供更短的 URL。
    如果设置了分享密码，返回需要验证的提示。
    """
    service = ConversationService(db)
    conversation = await service.get_conversation_by_token(share_token)
    if not conversation:
        raise HTTPException(status_code=404, detail="分享链接无效或已过期")

    # 校验过期时间
    from app.utils.time_utils import get_utc_now
    if conversation.share_expire_at and get_utc_now() > conversation.share_expire_at:
        raise HTTPException(status_code=410, detail="分享链接已过期")

    # 如果设置了密码，返回需要验证的提示
    if conversation.share_password:
        return {"requires_password": True, "has_password": True}

    # 无密码，直接返回数据
    data = await service.get_session_data(conversation.id)
    if not data:
        raise HTTPException(status_code=404, detail="分享链接无效或已过期")
    return data


@router.post("/share/{share_token}/verify")
@limiter.limit("10/minute")
async def verify_shared_session(
    request: Request,
    share_token: str,
    data: VerifySharePasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """验证分享密码后访问会话数据（无需认证）"""
    service = ConversationService(db)
    conversation = await service.get_conversation_by_token(share_token)
    if not conversation:
        raise HTTPException(status_code=404, detail="分享链接无效或已过期")

    # 校验过期时间
    from app.utils.time_utils import get_utc_now
    if conversation.share_expire_at and get_utc_now() > conversation.share_expire_at:
        raise HTTPException(status_code=410, detail="分享链接已过期")

    # 校验密码
    if not conversation.share_password:
        raise HTTPException(status_code=400, detail="该分享链接未设置密码")

    from app.core.security import verify_password
    if not verify_password(data.password, conversation.share_password):
        raise HTTPException(status_code=403, detail="分享密码错误")

    # 密码正确，返回数据
    session_data = await service.get_session_data(conversation.id)
    if not session_data:
        raise HTTPException(status_code=404, detail="分享链接无效或已过期")
    return session_data
