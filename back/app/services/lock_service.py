"""全局锁服务

实现会诊全局锁机制：
- 基于单点登录的会话隔离
- 原子性获取/释放锁
- 自动过期机制
"""
import asyncio
import uuid
import logging
from typing import Optional, Tuple

from app.core.redis import redis_client

logger = logging.getLogger(__name__)

class DistributedLock:
    """分布式锁实现"""

    def __init__(self, lock_key: str, lock_value: Optional[str] = None, expire_seconds: int = 3600):
        self.lock_key = f"lock:{lock_key}"
        self.lock_value = lock_value or str(uuid.uuid4())
        self.expire_seconds = expire_seconds
        self._acquired = False

    async def acquire(self) -> bool:
        """尝试获取锁"""
        acquired = await redis_client.set(
            self.lock_key,
            self.lock_value,
            nx=True,  # Only set if not exists
            ex=self.expire_seconds
        )
        self._acquired = acquired is not None
        return self._acquired

    async def release(self) -> bool:
        """释放锁 (仅当持有锁时)"""
        if not self._acquired:
            return False

        # 使用Lua脚本确保原子性
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = await redis_client.eval(lua_script, 1, self.lock_key, self.lock_value)
        self._acquired = False
        return result == 1

    async def extend(self, additional_seconds: int) -> bool:
        """延长锁的过期时间"""
        if not self._acquired:
            return False

        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        result = await redis_client.eval(
            lua_script, 1, self.lock_key, self.lock_value, str(additional_seconds)
        )
        return result == 1

    async def is_locked(self) -> bool:
        """检查锁是否被持有"""
        value = await redis_client.get(self.lock_key)
        return value is not None

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()


class ConsultationLockService:
    """会诊全局锁服务（基于单点登录的会话隔离）"""

    def __init__(self):
        """初始化会诊锁服务"""
        pass

    async def acquire_global_lock(
        self,
        user_id: int,
        timeout: int = 3600
    ) -> Tuple[bool, Optional[str]]:
        """
        获取全局会诊锁

        Args:
            user_id: 用户ID（基于单点登录，唯一标识当前用户）
            timeout: 锁超时时间（秒），默认1小时

        Returns:
            (成功标志, 锁值或错误消息)
        """
        lock_key = f"consultation:global:user:{user_id}"
        lock_value = str(uuid.uuid4())

        try:
            # 使用SET NX EX原子操作
            result = await redis_client.set(
                lock_key,
                lock_value,
                nx=True,  # 仅当key不存在时设置
                ex=timeout  # 设置过期时间
            )

            if result:
                logger.info(f"用户 {user_id} 获取会诊锁成功: {lock_value}")
                return True, lock_value
            else:
                # 获取当前锁的TTL
                ttl = await redis_client.ttl(lock_key)
                logger.warning(f"用户 {user_id} 获取会诊锁失败，锁被占用，剩余时间: {ttl}秒")
                return False, f"您有正在进行的会诊，请等待{ttl // 60}分钟后再试"

        except Exception as e:
            logger.error(f"获取会诊锁失败: {e}", exc_info=True)
            return False, f"获取锁失败: {str(e)}"

    async def release_global_lock(
        self,
        user_id: int,
        lock_value: str
    ) -> bool:
        """
        释放全局会诊锁

        Args:
            user_id: 用户ID
            lock_value: 锁值（必须匹配）

        Returns:
            是否成功释放
        """
        lock_key = f"consultation:global:user:{user_id}"

        try:
            # 使用Lua脚本确保原子性
            lua_script = """
            local key = KEYS[1]
            local expected_value = ARGV[1]

            local current_value = redis.call('GET', key)
            if current_value == expected_value then
                redis.call('DEL', key)
                return 1
            else
                return 0
            end
            """

            result = await redis_client.eval(lua_script, 1, lock_key, lock_value)

            if result == 1:
                logger.info(f"用户 {user_id} 释放会诊锁成功: {lock_value}")
                return True
            else:
                logger.warning(f"用户 {user_id} 释放会诊锁失败，锁值不匹配或锁已过期")
                return False

        except Exception as e:
            logger.error(f"释放会诊锁失败: {e}", exc_info=True)
            return False

    async def extend_lock_ttl(
        self,
        user_id: int,
        lock_value: str,
        additional_time: int
    ) -> bool:
        """
        延长锁的过期时间

        Args:
            user_id: 用户ID
            lock_value: 锁值
            additional_time: 延长的时间（秒）

        Returns:
            是否成功延长
        """
        lock_key = f"consultation:global:user:{user_id}"

        try:
            # 使用Lua脚本确保原子性
            lua_script = """
            local key = KEYS[1]
            local expected_value = ARGV[1]
            local additional_time = tonumber(ARGV[2])

            local current_value = redis.call('GET', key)
            if current_value == expected_value then
                local current_ttl = redis.call('TTL', key)
                if current_ttl > 0 then
                    redis.call('EXPIRE', key, current_ttl + additional_time)
                    return 1
                end
            end
            return 0
            """

            result = await redis_client.eval(lua_script, 1, lock_key, lock_value, additional_time)

            if result == 1:
                logger.info(f"用户 {user_id} 延长会诊锁TTL成功: +{additional_time}秒")
                return True
            else:
                logger.warning(f"用户 {user_id} 延长会诊锁TTL失败")
                return False

        except Exception as e:
            logger.error(f"延长锁TTL失败: {e}", exc_info=True)
            return False

    async def get_lock_info(
        self,
        user_id: int
    ) -> Optional[dict]:
        """
        获取锁信息（用于前端提示）

        Args:
            user_id: 用户ID

        Returns:
            {"lock_value": str, "ttl": int} 或 None
        """
        lock_key = f"consultation:global:user:{user_id}"

        try:
            lock_value = await redis_client.get(lock_key)
            if lock_value:
                ttl = await redis_client.ttl(lock_key)
                lock_value_str = lock_value.decode() if isinstance(lock_value, bytes) else lock_value
                return {
                    "lock_value": lock_value_str,
                    "ttl": ttl
                }
            return None

        except Exception as e:
            logger.error(f"获取锁信息失败: {e}", exc_info=True)
            return None

    async def force_release_lock(
        self,
        user_id: int
    ) -> bool:
        """
        强制释放锁（管理员功能）

        Args:
            user_id: 用户ID

        Returns:
            是否成功
        """
        lock_key = f"consultation:global:user:{user_id}"

        try:
            result = await redis_client.delete(lock_key)
            if result:
                logger.warning(f"管理员强制释放用户 {user_id} 的会诊锁")
                return True
            return False

        except Exception as e:
            logger.error(f"强制释放锁失败: {e}", exc_info=True)
            return False


# 全局实例
consultation_lock_service = ConsultationLockService()
