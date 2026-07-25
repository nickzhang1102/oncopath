"""缓存服务层 - 分类映射缓存管理"""
import time
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.image_report import ImageCategory


class CategoryCacheService:
    """图片分类缓存服务

    使用进程级缓存存储 ImageCategory 映射数据，避免重复查询。
    数据量小、变更频率低，适合内存缓存。
    """

    def __init__(self, ttl: int = 3600):
        """初始化缓存服务

        Args:
            ttl: 缓存过期时间（秒），默认1小时
        """
        self._cache: dict = {}
        self._cache_ts: float = 0
        self._ttl: int = ttl
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get_category_map(self, db: AsyncSession) -> dict:
        """获取分类映射，带缓存和并发锁

        Args:
            db: 数据库会话

        Returns:
            dict: {category_key: {category_name, icon, color}}
        """
        now = time.time()
        if self._cache and (now - self._cache_ts) < self._ttl:
            return self._cache

        async with self._lock:
            # 双重检查：获取锁后再次检查缓存是否已被其他协程刷新
            if self._cache and (now - self._cache_ts) < self._ttl:
                return self._cache

            result = await db.execute(
                select(
                    ImageCategory.category_key,
                    ImageCategory.category_name,
                    ImageCategory.icon,
                    ImageCategory.color,
                ).where(ImageCategory.is_active == True)
            )

            self._cache = {
                row.category_key: {
                    "category_name": row.category_name,
                    "icon": row.icon,
                    "color": row.color,
                }
                for row in result.all()
            }
            self._cache_ts = now
            return self._cache

    def clear_cache(self) -> None:
        """手动清除缓存（用于管理后台修改分类后刷新）"""
        self._cache = {}
        self._cache_ts = 0


# 全局单例
category_cache_service = CategoryCacheService()