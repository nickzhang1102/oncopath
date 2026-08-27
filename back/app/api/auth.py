from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging

logger = logging.getLogger(__name__)

from app.core.rate_limit import limiter
from app.core.config import settings

from app.core.database import get_db
from app.core.redis import redis_client
from app.core.security import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token, decode_token
)
from app.schemas.user import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    WechatLoginRequest, WechatBindRequest,
    ForgotPasswordRequest, ResetPasswordRequest
)
from app.models.user import LoginAccount, WechatBinding
from app.services.session_service import SessionService

router = APIRouter()
security = HTTPBearer()

# 登录失败限制配置
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 900  # 15分钟

# Redis Lua脚本：原子性地检查并增加登录失败次数
# 仅在首次失败时设置 TTL，避免每次失败都延长锁定时间
LOGIN_ATTEMPT_SCRIPT = """
local key = KEYS[1]
local max_attempts = tonumber(ARGV[1])
local ttl = tonumber(ARGV[2])

local current = tonumber(redis.call('GET', key) or '0')
if current >= max_attempts then
    local remaining_ttl = redis.call('TTL', key)
    return {-1, remaining_ttl}
end

local new_count = redis.call('INCR', key)
if new_count == 1 then
    redis.call('EXPIRE', key, ttl)
end

return {new_count, redis.call('TTL', key)}
"""

REFRESH_CONSUME_SCRIPT = """
local value = redis.call('GET', KEYS[1])
if not value then return 0 end
redis.call('DEL', KEYS[1])
return value
"""


REFRESH_PURGE_SCRIPT = """
local members = redis.call('SMEMBERS', KEYS[1])
for _, jti in ipairs(members) do
    redis.call('DEL', 'refresh_token:' .. jti)
end
redis.call('DEL', KEYS[1])
return #members
"""


def _refresh_token_key(jti: str) -> str:
    return f"refresh_token:{jti}"


def _refresh_index_key(account_id: int) -> str:
    return f"refresh_tokens_index:{account_id}"


async def _store_refresh_jti(account_id: int, token: str) -> None:
    payload = decode_token(token) or {}
    jti = str(payload.get("jti") or "")
    if not jti:
        return
    ttl_seconds = max(int(settings.REFRESH_TOKEN_EXPIRE_DAYS) * 86400, 60)
    index_key = _refresh_index_key(account_id)
    await redis_client.sadd(index_key, jti)
    await redis_client.expire(index_key, ttl_seconds)
    await redis_client.set(_refresh_token_key(jti), str(account_id), ex=ttl_seconds)


async def _consume_refresh_jti(account_id: int, jti: str) -> bool:
    if not jti:
        return False
    consumed = await redis_client.eval(REFRESH_CONSUME_SCRIPT, 1, _refresh_token_key(jti))
    return str(consumed or "") == str(account_id)


async def _purge_refresh_tokens(account_id: int) -> int:
    """撤销该账号名下全部刷新令牌（登出/重置密码/单点登录重登）。"""
    return int(await redis_client.eval(REFRESH_PURGE_SCRIPT, 1, _refresh_index_key(account_id)))


# 依赖注入函数 - 必须在使用前定义
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> LoginAccount:
    """获取当前用户（验证单点登录会话）"""
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的访问令牌"
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌缺少用户标识"
        )
    try:
        account_id = int(sub)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌用户标识无效"
        )
    token_jti = payload.get("jti")

    # 验证会话（单点登录检查）
    session_service = SessionService(redis_client)
    is_valid, reason = await session_service.validate_session(
        user_id=account_id,
        token_jti=token_jti
    )

    if not is_valid:
        logger.warning(f"用户 {account_id} 会话验证失败: {reason}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=reason  # "已在其他设备登录" 或 "Token已被撤销"
        )

    # 查询用户
    result = await db.execute(
        select(LoginAccount).where(LoginAccount.account_id == account_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )

    return user


async def get_current_admin_user(
    current_user: LoginAccount = Depends(get_current_user)
) -> LoginAccount:
    """校验当前用户是否为管理员"""
    if current_user.account_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    if current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已禁用"
        )
    return current_user


@router.post("/register", response_model=UserResponse)
@limiter.limit("5/minute")
async def register(user_data: UserCreate, request: Request, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    try:
        logger.info(f"开始注册用户: {user_data.username}")

        # 检查用户名是否已存在
        result = await db.execute(
            select(LoginAccount).where(LoginAccount.username == user_data.username)
        )
        if result.scalar_one_or_none():
            logger.warning(f"用户名已存在: {user_data.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )

        # 创建用户
        logger.info(f"创建用户: {user_data.username}")
        new_user = LoginAccount(
            username=user_data.username,
            password=get_password_hash(user_data.password),
            phone=user_data.phone,
            account_name=user_data.account_name or user_data.username
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        logger.info(f"用户创建成功: ID={new_user.account_id}")

        return new_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注册失败: {type(e).__name__}: {e}", exc_info=True)
        raise


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    login_data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """用户登录（单点登录，自动踢下线旧会话）"""
    client_key = f"login_attempts:{login_data.username}"

    # 使用Lua脚本原子性检查登录限制
    result = await redis_client.eval(
        LOGIN_ATTEMPT_SCRIPT,
        1,
        client_key,
        MAX_LOGIN_ATTEMPTS,
        LOGIN_LOCKOUT_SECONDS
    )
    count, ttl_or_remaining = result

    # 如果已达到限制
    if count == -1:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"登录失败次数过多，请{ttl_or_remaining // 60}分钟后重试"
        )

    # 查找用户
    user_result = await db.execute(
        select(LoginAccount).where(LoginAccount.username == login_data.username)
    )
    user = user_result.scalar_one_or_none()

    # 验证密码
    if not user or not verify_password(login_data.password, user.password):
        # Lua脚本已经原子性地增加了计数，无需额外操作
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    if user.status != 'active':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )

    # 清除失败记录
    await redis_client.delete(client_key)

    # 获取设备信息
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # 生成token
    access_token = create_access_token(
        user.account_id,
        device_info=f"{client_ip}|{user_agent[:100]}"  # 限制长度
    )
    # 单点登录重登：先撤销名下全部旧刷新令牌，再签发新令牌
    await _purge_refresh_tokens(user.account_id)
    refresh_token = create_refresh_token(user.account_id)
    await _store_refresh_jti(user.account_id, refresh_token)

    # 解析token获取jti
    payload = decode_token(access_token)
    token_jti = payload.get("jti")

    # 创建会话（踢下线旧会话）
    session_service = SessionService(redis_client)
    await session_service.create_session(
        user_id=user.account_id,
        token_jti=token_jti,
        expires_in=60 * 60,  # 1小时
        device_info={
            "ip": client_ip,
            "user_agent": user_agent[:200]  # 限制长度
        }
    )

    logger.info(f"用户 {user.username} 登录成功（单点登录）")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=60 * 60  # 60分钟
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """刷新访问令牌（更新会话）"""
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )

    account_id = int(payload.get("sub"))
    refresh_jti = payload.get("jti")

    if not await _consume_refresh_jti(account_id, str(refresh_jti or "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌已使用或已失效",
        )

    # 验证用户状态
    result = await db.execute(
        select(LoginAccount).where(LoginAccount.account_id == account_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )

    if user.status != 'active':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )

    # 生成新token
    access_token = create_access_token(user.account_id)
    new_refresh_token = create_refresh_token(user.account_id)
    await _store_refresh_jti(user.account_id, new_refresh_token)

    # 更新会话（使用新的jti）
    new_payload = decode_token(access_token)
    new_jti = new_payload.get("jti")

    session_service = SessionService(redis_client)
    await session_service.create_session(
        user_id=user.account_id,
        token_jti=new_jti,
        expires_in=60 * 60  # 1小时
    )

    logger.info(f"用户 {user.username} 刷新Token成功")

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=60 * 60
    )

@router.post("/logout")
async def logout(current_user: LoginAccount = Depends(get_current_user)):
    """用户登出（撤销会话）"""
    # 撤销会话并吊销该账号的全部刷新令牌
    session_service = SessionService(redis_client)
    await session_service.revoke_session(current_user.account_id)
    await _purge_refresh_tokens(current_user.account_id)

    logger.info(f"用户 {current_user.username} 已登出")

    return {"message": "登出成功"}

@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """忘记密码 - 生成重置令牌

    流程：用户输入用户名 → 后端验证用户存在 → 生成 Redis 限时令牌 → 返回令牌
    未来接入 SMS/Email 时，令牌不再直接返回，而是通过通道发送验证码。
    """
    # 查找用户
    result = await db.execute(
        select(LoginAccount).where(LoginAccount.username == data.username)
    )
    user = result.scalar_one_or_none()

    # 无论用户是否存在，都返回相同提示，防止用户名枚举
    if not user:
        # 添加随机延迟防止时序攻击
        import asyncio
        await asyncio.sleep(0.3)
        return {"message": "如果用户名存在，重置令牌已生成", "reset_token": None}

    # 检查用户状态
    if user.status != 'active':
        return {"message": "如果用户名存在，重置令牌已生成", "reset_token": None}

    # 生成重置令牌（6位数字验证码，方便未来 SMS 使用）
    import secrets
    reset_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])

    # 存入 Redis，15分钟有效
    redis_key = f"password_reset:{data.username}"
    await redis_client.setex(redis_key, 900, reset_code)

    logger.info(f"用户 {data.username} 请求密码重置，令牌已生成")

    # 生产环境通过 SMS/Email 发送验证码，绝不在 API 响应中返回
    # 如需调试，请查看日志输出或 Redis 中存储的验证码
    logger.debug(f"密码重置验证码（仅调试日志）: {reset_code}")

    return {
        "message": "如果用户名存在，重置验证码已发送",
        "expires_in": 900
    }


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """重置密码 - 使用重置令牌设置新密码"""
    # 从 Redis 获取令牌
    redis_key = f"password_reset:{data.username}"
    attempt_key = f"password_reset_attempts:{data.username}"
    stored_token = await redis_client.get(redis_key)

    attempts = await redis_client.get(attempt_key)
    if attempts and int(attempts) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="重置尝试次数过多，请 15 分钟后重试",
        )

    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重置令牌无效或已过期"
        )

    # 恒定时间比较，防止时序攻击
    import hmac
    if not hmac.compare_digest(stored_token, data.reset_token):
        count = await redis_client.incr(attempt_key)
        if count == 1:
            await redis_client.expire(attempt_key, 900)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重置令牌无效或已过期"
        )

    # 查找用户
    result = await db.execute(
        select(LoginAccount).where(LoginAccount.username == data.username)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 更新密码
    user.password = get_password_hash(data.new_password)
    await db.commit()

    # 删除已使用的重置令牌
    await redis_client.delete(redis_key)
    await redis_client.delete(attempt_key)

    # 撤销所有现有会话与刷新令牌，强制重新登录
    session_service = SessionService(redis_client)
    await session_service.revoke_session(user.account_id)
    await _purge_refresh_tokens(user.account_id)

    logger.info(f"用户 {data.username} 密码重置成功")

    return {"message": "密码重置成功，请重新登录"}


@router.post("/wechat/login", response_model=TokenResponse)
async def wechat_login(
    data: WechatLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """微信登录"""
    # TODO: 实现微信OAuth登录
    raise HTTPException(status_code=501, detail="功能开发中")

@router.post("/wechat/bind")
async def bind_wechat(
    data: WechatBindRequest,
    current_user: LoginAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """绑定微信"""
    # TODO: 实现微信绑定
    raise HTTPException(status_code=501, detail="功能开发中")
