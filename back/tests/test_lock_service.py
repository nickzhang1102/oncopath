import pytest
import asyncio
from app.services.lock_service import DistributedLock

class TestDistributedLock:
    @pytest.mark.asyncio
    async def test_lock_acquire_and_release(self):
        lock = DistributedLock("test_lock", expire_seconds=10)

        # 获取锁
        acquired = await lock.acquire()
        assert acquired is True

        # 检查锁状态
        is_locked = await lock.is_locked()
        assert is_locked is True

        # 释放锁
        released = await lock.release()
        assert released is True

        # 检查锁状态
        is_locked = await lock.is_locked()
        assert is_locked is False

    @pytest.mark.asyncio
    async def test_lock_exclusive(self):
        lock1 = DistributedLock("exclusive_test", lock_value="owner1", expire_seconds=10)
        lock2 = DistributedLock("exclusive_test", lock_value="owner2", expire_seconds=10)

        # 第一个获取成功
        assert await lock1.acquire() is True

        # 第二个获取失败
        assert await lock2.acquire() is False

        # 释放后第二个可以获取
        await lock1.release()
        assert await lock2.acquire() is True
        await lock2.release()

    @pytest.mark.asyncio
    async def test_lock_context_manager(self):
        async with DistributedLock("context_test", expire_seconds=10) as lock:
            assert await lock.is_locked() is True

        # 退出上下文后锁已释放
        lock_check = DistributedLock("context_test")
        assert await lock_check.is_locked() is False

    @pytest.mark.asyncio
    async def test_consultation_global_lock(self):
        lock = DistributedLock("consultation_global", expire_seconds=10)
        assert lock.lock_key == "lock:consultation_global"

        acquired = await lock.acquire()
        assert acquired is True
        await lock.release()
