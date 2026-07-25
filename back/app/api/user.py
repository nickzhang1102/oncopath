from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
import asyncio
import json
import logging

from app.core.database import get_db
from app.api.auth import get_current_user
from app.core.security import verify_password, get_password_hash
from app.core.redis import redis_client
from app.models.user import LoginAccount
from app.models.notification import Notification
from app.schemas.user import (
    UserResponse, UserProfileUpdate, PasswordChangeRequest,
    PrivacySettings, PrivacySettingsUpdate,
    NotificationResponse, NotificationListResponse, NotificationCreate
)
from app.services.notification_service import create_and_publish_notification

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_profile(
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取用户信息"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    update_data: UserProfileUpdate,
    current_user: LoginAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新用户信息"""
    if update_data.account_name is not None:
        current_user.account_name = update_data.account_name
    if update_data.phone is not None:
        current_user.phone = update_data.phone

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.put("/password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: LoginAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """修改密码"""
    # 验证旧密码
    if not verify_password(password_data.old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    # 新密码不能与旧密码相同
    if verify_password(password_data.new_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不能与旧密码相同"
        )
    
    # 更新密码
    current_user.password = get_password_hash(password_data.new_password)
    await db.commit()
    
    return {"success": True, "message": "密码修改成功"}


@router.get("/privacy", response_model=PrivacySettings)
async def get_privacy_settings(
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取隐私设置"""
    return PrivacySettings(
        data_sharing_enabled=current_user.data_sharing_enabled if current_user.data_sharing_enabled is not None else True,
        notification_enabled=current_user.notification_enabled if current_user.notification_enabled is not None else True,
        email_notification=current_user.email_notification if current_user.email_notification is not None else False,
        sms_notification=current_user.sms_notification if current_user.sms_notification is not None else False
    )


@router.put("/privacy")
async def update_privacy_settings(
    settings: PrivacySettingsUpdate,
    current_user: LoginAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新隐私设置"""
    if settings.data_sharing_enabled is not None:
        current_user.data_sharing_enabled = settings.data_sharing_enabled
    if settings.notification_enabled is not None:
        current_user.notification_enabled = settings.notification_enabled
    if settings.email_notification is not None:
        current_user.email_notification = settings.email_notification
    if settings.sms_notification is not None:
        current_user.sms_notification = settings.sms_notification
    
    await db.commit()
    return {"success": True}


@router.get("/notifications", response_model=NotificationListResponse)
async def get_notifications(
    type: Optional[str] = Query(None, description="通知类型筛选"),
    is_read: Optional[bool] = Query(None, description="是否已读"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: LoginAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取通知列表"""
    # 构建查询条件
    conditions = [Notification.account_id == current_user.account_id]
    if type:
        conditions.append(Notification.type == type)
    if is_read is not None:
        conditions.append(Notification.is_read == is_read)
    
    # 查询总数
    count_query = select(func.count(Notification.notification_id)).where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 查询未读数
    unread_query = select(func.count(Notification.notification_id)).where(
        and_(
            Notification.account_id == current_user.account_id,
            Notification.is_read == False
        )
    )
    unread_result = await db.execute(unread_query)
    unread_count = unread_result.scalar()
    
    # 分页查询
    offset = (page - 1) * limit
    query = select(Notification).where(and_(*conditions)).order_by(
        Notification.created_at.desc()
    ).offset(offset).limit(limit)
    
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        unread_count=unread_count,
        page=page,
        limit=limit
    )


@router.post("/notifications", response_model=NotificationResponse)
async def create_notification(
    notification_data: NotificationCreate,
    current_user: LoginAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建通知（内部使用）— 同时推送到 SSE"""
    notification = await create_and_publish_notification(
        db=db,
        account_id=current_user.account_id,
        type=notification_data.type,
        title=notification_data.title,
        content=notification_data.content,
        extra_data=notification_data.extra_data,
    )
    return NotificationResponse.model_validate(notification)


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: LoginAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """标记通知为已读"""
    query = select(Notification).where(
        Notification.notification_id == notification_id,
        Notification.account_id == current_user.account_id
    )
    result = await db.execute(query)
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知不存在"
        )
    
    notification.is_read = True
    await db.commit()
    return {"success": True}


@router.put("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: LoginAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """标记所有通知为已读"""
    query = select(Notification).where(
        Notification.account_id == current_user.account_id,
        Notification.is_read == False
    )
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    updated_count = 0
    for notification in notifications:
        notification.is_read = True
        updated_count += 1
    
    await db.commit()
    return {"success": True, "updated_count": updated_count}


@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: LoginAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除通知"""
    query = select(Notification).where(
        Notification.notification_id == notification_id,
        Notification.account_id == current_user.account_id
    )
    result = await db.execute(query)
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知不存在"
        )
    
    await db.delete(notification)
    await db.commit()
    return {"success": True}


@router.get("/notifications/stream")
async def notification_stream(
    request: Request,
):
    """SSE 实时通知推送端点

    - 支持 Authorization header 认证（fetch + ReadableStream 方式）
    - 订阅 Redis channel: notifications:{account_id}
    - 首次连接推送最近 10 条未读通知
    - 心跳保活 30s
    - 断线自动清理
    """
    from app.core.security import decode_token

    # 从 Authorization header 提取 token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少有效的认证信息")

    token = auth_header[7:]  # 去掉 "Bearer " 前缀

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="无效的访问令牌")

    try:
        account_id = int(payload.get("sub"))
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="令牌用户标识无效")

    # 验证会话（SSO）
    from app.services.session_service import SessionService
    session_svc = SessionService(redis_client)
    jti = payload.get("jti", "")
    session_valid, _ = await session_svc.validate_session(account_id, jti)
    if not session_valid:
        raise HTTPException(status_code=401, detail="会话已过期")
    channel = f"notifications:{account_id}"

    async def event_generator():
        pubsub = None

        try:
            # 1. 推送历史快照（最近 10 条未读）
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as snapshot_db:
                result = await snapshot_db.execute(
                    select(Notification)
                    .where(Notification.account_id == account_id, Notification.is_read == False)
                    .order_by(Notification.created_at.desc())
                    .limit(10)
                )
                recent = list(reversed(result.scalars().all()))  # 时间正序
                for n in recent:
                    payload = NotificationResponse.model_validate(n).model_dump(mode="json")
                    yield f"event: notification\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

            # 2. 订阅 Redis pubsub
            pubsub = redis_client.get_pubsub()
            await pubsub.subscribe(channel)

            # 3. 消费循环：pubsub 消息 + 心跳
            heartbeat_interval = 30
            while True:
                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True, timeout=heartbeat_interval),
                        timeout=heartbeat_interval,
                    )
                    if message and message["type"] == "message":
                        yield f"event: notification\ndata: {message['data']}\n\n"
                    else:
                        yield ": keepalive\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"

        except asyncio.CancelledError:
            logger.debug(f"SSE 连接关闭: account_id={account_id}")
        except Exception as e:
            logger.error(f"SSE 异常: account_id={account_id}, error={e}")
        finally:
            if pubsub:
                try:
                    await pubsub.unsubscribe(channel)
                    await pubsub.close()
                except Exception:
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )