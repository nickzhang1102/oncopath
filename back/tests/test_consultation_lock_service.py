"""会诊全局锁服务测试"""
import pytest

from app.services.lock_service import consultation_lock_service


@pytest.mark.asyncio
async def test_acquire_lock_success(redis_client):
    """测试成功获取锁"""
    success, lock_value = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )

    assert success is True
    assert lock_value is not None

    # 验证锁已存储
    stored_value = await redis_client.get("consultation:global:user:1")
    assert stored_value == lock_value


@pytest.mark.asyncio
async def test_acquire_lock_conflict(redis_client):
    """测试并发获取锁失败"""
    # 第一次获取锁
    success1, lock_value1 = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )
    assert success1 is True

    # 第二次获取锁（应失败）
    success2, lock_value2 = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )
    assert success2 is False
    assert "正在进行的会诊" in lock_value2


@pytest.mark.asyncio
async def test_release_lock_success(redis_client):
    """测试成功释放锁"""
    # 获取锁
    success, lock_value = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )
    assert success is True

    # 释放锁
    result = await consultation_lock_service.release_global_lock(
        user_id=1,
        lock_value=lock_value
    )
    assert result is True

    # 验证锁已删除
    stored_value = await redis_client.get("consultation:global:user:1")
    assert stored_value is None


@pytest.mark.asyncio
async def test_release_lock_wrong_value(redis_client):
    """测试错误value无法释放锁"""
    # 获取锁
    success, lock_value = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )
    assert success is True

    # 尝试用错误的value释放锁
    result = await consultation_lock_service.release_global_lock(
        user_id=1,
        lock_value="wrong-value"
    )
    assert result is False

    # 验证锁仍然存在
    stored_value = await redis_client.get("consultation:global:user:1")
    assert stored_value is not None


@pytest.mark.asyncio
async def test_lock_auto_expire(redis_client):
    """测试锁自动过期"""
    # 获取锁，1秒后过期
    success, lock_value = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=1
    )
    assert success is True

    # 等待过期
    import asyncio
    await asyncio.sleep(2)

    # 验证锁已过期
    stored_value = await redis_client.get("consultation:global:user:1")
    assert stored_value is None

    # 可以重新获取锁
    success2, lock_value2 = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )
    assert success2 is True


@pytest.mark.asyncio
async def test_extend_lock_ttl(redis_client):
    """测试延长锁TTL"""
    # 获取锁
    success, lock_value = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )
    assert success is True

    # 获取当前TTL
    ttl_before = await redis_client.ttl("consultation:global:user:1")

    # 延长TTL
    result = await consultation_lock_service.extend_lock_ttl(
        user_id=1,
        lock_value=lock_value,
        additional_time=1800
    )
    assert result is True

    # 验证TTL已延长
    ttl_after = await redis_client.ttl("consultation:global:user:1")
    assert ttl_after > ttl_before


@pytest.mark.asyncio
async def test_extend_lock_ttl_wrong_value(redis_client):
    """测试用错误value延长锁"""
    # 获取锁
    success, lock_value = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )
    assert success is True

    # 尝试用错误value延长
    result = await consultation_lock_service.extend_lock_ttl(
        user_id=1,
        lock_value="wrong-value",
        additional_time=1800
    )
    assert result is False


@pytest.mark.asyncio
async def test_get_lock_info(redis_client):
    """测试获取锁信息"""
    # 获取锁
    success, lock_value = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )
    assert success is True

    # 获取锁信息
    info = await consultation_lock_service.get_lock_info(user_id=1)

    assert info is not None
    assert info["lock_value"] == lock_value
    assert info["ttl"] > 0


@pytest.mark.asyncio
async def test_get_lock_info_no_lock(redis_client):
    """测试无锁时获取锁信息"""
    info = await consultation_lock_service.get_lock_info(user_id=1)
    assert info is None


@pytest.mark.asyncio
async def test_force_release_lock(redis_client):
    """测试强制释放锁"""
    # 获取锁
    success, lock_value = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )
    assert success is True

    # 强制释放锁（无需value）
    result = await consultation_lock_service.force_release_lock(user_id=1)
    assert result is True

    # 验证锁已删除
    stored_value = await redis_client.get("consultation:global:user:1")
    assert stored_value is None


@pytest.mark.asyncio
async def test_concurrent_acquire(redis_client):
    """测试并发获取锁"""
    import asyncio

    async def try_acquire(user_id):
        return await consultation_lock_service.acquire_global_lock(
            user_id=user_id,
            timeout=3600
        )

    # 并发尝试获取锁
    results = await asyncio.gather(
        try_acquire(1),
        try_acquire(1),
        try_acquire(1)
    )

    # 只有一个应该成功
    success_count = sum(1 for success, _ in results if success)
    assert success_count == 1


@pytest.mark.asyncio
async def test_different_users_locks(redis_client):
    """测试不同用户的锁互不影响"""
    # 用户1获取锁
    success1, lock_value1 = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )
    assert success1 is True

    # 用户2获取锁（应成功）
    success2, lock_value2 = await consultation_lock_service.acquire_global_lock(
        user_id=2,
        timeout=3600
    )
    assert success2 is True

    # 验证两个锁都存在
    stored_value1 = await redis_client.get("consultation:global:user:1")
    stored_value2 = await redis_client.get("consultation:global:user:2")
    assert stored_value1 == lock_value1
    assert stored_value2 == lock_value2
