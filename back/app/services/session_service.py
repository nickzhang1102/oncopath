"""会话管理服务

实现单点登录（SSO）核心功能：
- 会话创建与管理
- 踢下线机制
- Token黑名单
- 会话验证
"""
import json
import logging
from typing import Tuple, List, Optional

from redis.asyncio import Redis

from app.utils.time_utils import get_utc_now

logger = logging.getLogger(__name__)


class SessionService:
    """会话管理服务（基于Redis实现单点登录）"""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def create_session(
        self,
        user_id: int,
        token_jti: str,
        expires_in: int = 3600,
        device_info: Optional[dict] = None
    ) -> bool:
        """
        创建新会话（踢下线旧会话）

        Args:
            user_id: 用户ID
            token_jti: JWT唯一标识
            expires_in: 过期时间（秒），默认1小时
            device_info: 设备信息（可选）

        Returns:
            是否成功
        """
        session_key = f"session:user:{user_id}"

        try:
            # 检查是否存在旧会话
            old_jti = await self.redis.get(session_key)
            if old_jti:
                # 将旧Token加入黑名单
                old_jti_str = old_jti  # Redis decode_responses=True 已处理
                blacklist_key = f"token:blacklist:{old_jti_str}"

                # 获取旧会话的剩余TTL
                old_ttl = await self.redis.ttl(session_key)
                if old_ttl > 0:
                    # 黑名单TTL = 剩余有效时间
                    await self.redis.set(blacklist_key, "1", ex=old_ttl)

                logger.info(f"用户 {user_id} 旧会话已踢下线: jti={old_jti_str}")

                # 强制释放该用户的全局会诊锁
                await self._force_release_consultation_lock(user_id)

            # 存储新会话
            await self.redis.set(session_key, token_jti, ex=expires_in)

            # 记录在线状态
            online_key = f"user:online:{user_id}"
            online_value = json.dumps({
                "jti": token_jti,
                "device": device_info,
                "login_at": get_utc_now().isoformat()
            })
            await self.redis.set(online_key, online_value, ex=expires_in)

            logger.info(f"用户 {user_id} 创建新会话: jti={token_jti}, expires_in={expires_in}s")
            return True

        except Exception as e:
            logger.error(f"创建会话失败: {e}", exc_info=True)
            return False

    async def _force_release_consultation_lock(self, user_id: int) -> bool:
        """
        强制释放用户的全局会诊锁（内部方法）

        Args:
            user_id: 用户ID

        Returns:
            是否成功释放
        """
        lock_key = f"consultation:global:user:{user_id}"

        try:
            # 检查是否存在锁
            if await self.redis.exists(lock_key):
                # 强制删除锁
                result = await self.redis.delete(lock_key)
                if result:
                    logger.warning(f"用户 {user_id} 被踢下线，强制释放会诊锁")
                    return True
                else:
                    logger.warning(f"用户 {user_id} 会诊锁释放失败")
                    return False
            return True  # 没有锁也算成功

        except Exception as e:
            logger.error(f"强制释放会诊锁失败: {e}", exc_info=True)
            return False

    async def validate_session(
        self,
        user_id: int,
        token_jti: str
    ) -> Tuple[bool, str]:
        """
        验证会话有效性

        Args:
            user_id: 用户ID
            token_jti: JWT唯一标识

        Returns:
            (是否有效, 原因)
        """
        try:
            # 1. 检查黑名单
            blacklist_key = f"token:blacklist:{token_jti}"
            if await self.redis.exists(blacklist_key):
                logger.warning(f"用户 {user_id} Token在黑名单中: jti={token_jti}")
                return False, "Token已被撤销"

            # 2. 检查是否为当前有效会话
            session_key = f"session:user:{user_id}"
            current_jti = await self.redis.get(session_key)

            if not current_jti:
                logger.warning(f"用户 {user_id} 会话不存在或已过期")
                return False, "会话不存在或已过期"

            current_jti_str = current_jti  # Redis decode_responses=True 已处理

            if current_jti_str != token_jti:
                logger.warning(f"用户 {user_id} Token不匹配当前会话: current={current_jti_str}, token={token_jti}")
                return False, "已在其他设备登录"

            return True, "会话有效"

        except Exception as e:
            logger.error(f"验证会话失败: {e}", exc_info=True)
            return False, f"验证失败: {str(e)}"

    async def revoke_session(
        self,
        user_id: int
    ) -> bool:
        """
        撤销用户会话（登出）

        Args:
            user_id: 用户ID

        Returns:
            是否成功
        """
        try:
            session_key = f"session:user:{user_id}"
            jti = await self.redis.get(session_key)

            if jti:
                jti_str = jti  # Redis decode_responses=True 已处理

                # 加入黑名单
                blacklist_key = f"token:blacklist:{jti_str}"
                ttl = await self.redis.ttl(session_key)
                if ttl > 0:
                    await self.redis.set(blacklist_key, "1", ex=ttl)

                # 删除会话
                await self.redis.delete(session_key)
                await self.redis.delete(f"user:online:{user_id}")

                logger.info(f"用户 {user_id} 会话已撤销: jti={jti_str}")

            return True

        except Exception as e:
            logger.error(f"撤销会话失败: {e}", exc_info=True)
            return False

    async def extend_session_ttl(
        self,
        user_id: int,
        token_jti: str,
        additional_time: int
    ) -> bool:
        """
        延长会话TTL

        Args:
            user_id: 用户ID
            token_jti: JWT唯一标识
            additional_time: 延长的时间（秒）

        Returns:
            是否成功
        """
        try:
            session_key = f"session:user:{user_id}"

            # 验证会话是否匹配
            current_jti = await self.redis.get(session_key)
            if not current_jti:
                return False

            current_jti_str = current_jti  # Redis decode_responses=True 已处理
            if current_jti_str != token_jti:
                return False

            # 延长TTL
            current_ttl = await self.redis.ttl(session_key)
            if current_ttl > 0:
                new_ttl = current_ttl + additional_time
                await self.redis.expire(session_key, new_ttl)
                await self.redis.expire(f"user:online:{user_id}", new_ttl)
                logger.info(f"用户 {user_id} 会话TTL延长: +{additional_time}s, new_ttl={new_ttl}s")
                return True

            return False

        except Exception as e:
            logger.error(f"延长会话TTL失败: {e}", exc_info=True)
            return False

    async def get_online_users(self) -> List[dict]:
        """
        获取在线用户列表（管理功能）

        Returns:
            在线用户列表
        """
        try:
            pattern = "user:online:*"
            online_users = []

            async for key in self.redis.scan_iter(match=pattern):
                key_str = key  # Redis decode_responses=True 已处理
                user_id = key_str.split(":")[-1]
                info = await self.redis.get(key)
                if info:
                    info_str = info  # Redis decode_responses=True 已处理
                    online_users.append({
                        "user_id": int(user_id),
                        **json.loads(info_str)
                    })

            return online_users

        except Exception as e:
            logger.error(f"获取在线用户列表失败: {e}", exc_info=True)
            return []

    async def get_session_info(
        self,
        user_id: int
    ) -> Optional[dict]:
        """
        获取会话信息

        Args:
            user_id: 用户ID

        Returns:
            会话信息或None
        """
        try:
            session_key = f"session:user:{user_id}"
            jti = await self.redis.get(session_key)

            if jti:
                jti_str = jti  # Redis decode_responses=True 已处理
                ttl = await self.redis.ttl(session_key)

                # 获取在线状态信息
                online_key = f"user:online:{user_id}"
                online_info = await self.redis.get(online_key)
                device_info = None
                if online_info:
                    online_info_str = online_info  # Redis decode_responses=True 已处理
                    device_info = json.loads(online_info_str)

                return {
                    "jti": jti_str,
                    "ttl": ttl,
                    "device_info": device_info
                }

            return None

        except Exception as e:
            logger.error(f"获取会话信息失败: {e}", exc_info=True)
            return None