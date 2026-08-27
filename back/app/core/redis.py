import redis.asyncio as redis
from typing import Optional, Any
import json

from app.core.config import settings


class RedisClient:
    """Redis客户端封装"""

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    async def connect(self):
        """连接Redis"""
        self._client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True
        )

    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()

    async def ping(self) -> bool:
        """测试连接"""
        if not self._client:
            await self.connect()
        return await self._client.ping()

    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        if not self._client:
            await self.connect()
        value = await self._client.get(key)
        return value

    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """设置值

        Args:
            key: 键
            value: 值
            ex: 过期时间(秒)
            nx: 仅在键不存在时设置
        """
        if not self._client:
            await self.connect()

        kwargs = {}
        if ex:
            kwargs['ex'] = ex
        if nx:
            kwargs['nx'] = True

        result = await self._client.set(key, value, **kwargs)
        return result

    async def delete(self, key: str) -> int:
        """删除键"""
        if not self._client:
            await self.connect()
        return await self._client.delete(key)

    async def exists(self, key: str) -> int:
        """检查键是否存在"""
        if not self._client:
            await self.connect()
        return await self._client.exists(key)

    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        if not self._client:
            await self.connect()
        return await self._client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """获取剩余过期时间"""
        if not self._client:
            await self.connect()
        return await self._client.ttl(key)

    async def incr(self, key: str) -> int:
        """自增"""
        if not self._client:
            await self.connect()
        return await self._client.incr(key)

    async def decr(self, key: str) -> int:
        """自减"""
        if not self._client:
            await self.connect()
        return await self._client.decr(key)

    async def set_json(self, key: str, value: Any, ex: Optional[int] = None):
        """存储JSON数据"""
        json_str = json.dumps(value, ensure_ascii=False)
        await self.set(key, json_str, ex=ex)

    async def get_json(self, key: str) -> Optional[Any]:
        """获取JSON数据"""
        value = await self.get(key)
        if value:
            return json.loads(value)
        return None

    async def sadd(self, key: str, *values: str) -> int:
        """向集合添加成员"""
        if not self._client:
            await self.connect()
        return await self._client.sadd(key, *values)

    async def eval(self, script: str, num_keys: int, *keys_and_args) -> Any:
        """执行Lua脚本"""
        if not self._client:
            await self.connect()
        return await self._client.eval(script, num_keys, *keys_and_args)

    async def publish(self, channel: str, message: str) -> int:
        """发布消息到 Redis channel"""
        if not self._client:
            await self.connect()
        return await self._client.publish(channel, message)

    def get_pubsub(self) -> redis.client.PubSub:
        """获取 PubSub 对象（用于订阅）"""
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client.pubsub()


# 全局Redis客户端实例
redis_client = RedisClient()
