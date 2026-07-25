from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
import jwt
import uuid

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(
    account_id: int,
    expires_delta: Optional[timedelta] = None,
    device_info: Optional[str] = None
) -> str:
    """创建访问令牌（含唯一jti，支持单点登录）

    Args:
        account_id: 用户ID
        expires_delta: 过期时间间隔
        device_info: 设备信息（可选）

    Returns:
        JWT访问令牌
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(account_id),
        "exp": expire,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),  # JWT唯一标识，用于单点登录会话管理
    }

    # 可选：添加设备信息
    if device_info:
        to_encode["device"] = device_info

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    return encoded_jwt


def create_refresh_token(account_id: int) -> str:
    """创建刷新令牌（含唯一jti）

    Args:
        account_id: 用户ID

    Returns:
        JWT刷新令牌
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode: Dict[str, Any] = {
        "sub": str(account_id),
        "exp": expire,
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),  # JWT唯一标识
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """解码令牌

    Returns:
        成功返回payload字典
        Token过期返回None（调用方应返回401）
        Token无效返回None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        # Token已过期
        return None
    except jwt.InvalidTokenError:
        # Token无效（签名错误、格式错误等）
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[int]:
    """验证令牌并返回用户ID"""
    payload = decode_token(token)
    if not payload:
        return None

    # 检查令牌类型
    if payload.get("type") != token_type:
        return None

    # 获取用户ID
    account_id = payload.get("sub")
    if not account_id:
        return None

    return int(account_id)
