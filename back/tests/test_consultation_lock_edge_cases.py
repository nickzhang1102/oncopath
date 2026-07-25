"""会诊锁边界情况测试

测试踢下线时的锁处理逻辑
"""
import pytest
import asyncio

from app.services.session_service import SessionService
from app.services.lock_service import consultation_lock_service


@pytest.mark.asyncio
async def test_lock_released_on_kickoff(redis_client):
    """测试踢下线时锁被释放"""
    # 清理环境
    await redis_client.delete("consultation:global:user:1")
    await redis_client.delete("session:user:1")

    session_service = SessionService(redis_client)

    # 1. 设备A创建会话
    await session_service.create_session(
        user_id=1,
        token_jti="device-a-token",
        expires_in=3600
    )

    # 2. 设备A获取锁（模拟开始会诊）
    success_a, lock_value_a = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )
    assert success_a is True

    # 验证锁存在
    lock_info = await consultation_lock_service.get_lock_info(user_id=1)
    assert lock_info is not None

    # 3. 设备B登录（踢下线设备A）
    await session_service.create_session(
        user_id=1,
        token_jti="device-b-token",
        expires_in=3600
    )

    # 4. 验证设备A的Token在黑名单
    in_blacklist = await redis_client.exists("token:blacklist:device-a-token")
    assert in_blacklist == 1

    # 5. 验证锁已被释放（关键）
    lock_info = await consultation_lock_service.get_lock_info(user_id=1)
    assert lock_info is None, "锁应该已被释放"

    # 6. 设备B可以获取锁
    success_b, lock_value_b = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )
    assert success_b is True


@pytest.mark.asyncio
async def test_device_a_kicked_while_consulting(redis_client):
    """测试设备A会诊中被踢下线的完整流程"""
    session_service = SessionService(redis_client)

    # 1. 设备A登录并开始会诊（获取锁）
    await session_service.create_session(
        user_id=1,
        token_jti="device-a-token",
        expires_in=3600
    )
    success_a, lock_value_a = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )
    assert success_a is True

    # 2. 设备B登录踢下线设备A
    await session_service.create_session(
        user_id=1,
        token_jti="device-b-token",
        expires_in=3600
    )

    # 3. 验证设备A的Token失效
    is_valid, reason = await session_service.validate_session(
        user_id=1,
        token_jti="device-a-token"  # 假设设备A的token_jti
    )
    assert is_valid is False
    assert reason == "Token已被撤销"

    # 4. 验证锁已被释放
    lock_info = await consultation_lock_service.get_lock_info(user_id=1)
    assert lock_info is None

    # 5. 设备B可以开始会诊
    success_b, lock_value_b = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )
    assert success_b is True


@pytest.mark.asyncio
async def test_lock_value_mismatch_after_kickoff(redis_client):
    """测试踢下线后设备A尝试释放锁（value不匹配）"""
    session_service = SessionService(redis_client)

    # 1. 设备A登录并获取锁
    await session_service.create_session(
        user_id=1,
        token_jti="device-a-token",
        expires_in=3600
    )
    success_a, lock_value_a = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )
    assert success_a is True

    # 2. 设备B登录踢下线设备A
    await session_service.create_session(
        user_id=1,
        token_jti="device-b-token",
        expires_in=3600
    )

    # 3. 设备A尝试释放锁（finally块可能执行）
    result = await consultation_lock_service.release_global_lock(
        user_id=1,
        lock_value=lock_value_a
    )

    # 锁已被设备B删除或value不匹配，释放失败
    # 这是正常行为，不影响系统
    assert result is False


@pytest.mark.asyncio
async def test_concurrent_kickoff_and_consultation(redis_client):
    """测试并发场景：踢下线和会诊同时发生"""
    session_service = SessionService(redis_client)

    await session_service.create_session(
        user_id=1,
        token_jti="device-a-token",
        expires_in=3600
    )

    async def device_a_consultation():
        """设备A的会诊流程"""
        # 获取锁
        success, lock_value = await consultation_lock_service.acquire_global_lock(
            user_id=1,
            timeout=3600
        )
        return success, lock_value

    async def device_b_login():
        """设备B登录踢下线"""
        await asyncio.sleep(0.1)  # 稍微延迟
        await session_service.create_session(
            user_id=1,
            token_jti="device-b-token",
            expires_in=3600
        )

    # 并发执行
    (success_a, lock_value_a), _ = await asyncio.gather(
        device_a_consultation(),
        device_b_login()
    )

    # 设备A可能获取锁成功，但随即被踢下线
    # 锁应该已被释放
    lock_info = await consultation_lock_service.get_lock_info(user_id=1)
    assert lock_info is None, "锁应该已被踢下线操作释放"

    # 设备B可以获取锁
    success_b, lock_value_b = await consultation_lock_service.acquire_global_lock(
        user_id=1,
        timeout=3600
    )
    assert success_b is True


@pytest.mark.asyncio
async def test_old_device_token_blacklisted(redis_client):
    """测试旧设备Token被加入黑名单"""
    session_service = SessionService(redis_client)

    # 1. 设备A登录
    await session_service.create_session(
        user_id=1,
        token_jti="old-device-jti",
        expires_in=3600
    )

    # 2. 设备B登录踢下线设备A
    await session_service.create_session(
        user_id=1,
        token_jti="new-device-jti",
        expires_in=3600
    )

    # 3. 验证设备A的Token在黑名单
    in_blacklist = await redis_client.exists("token:blacklist:old-device-jti")
    assert in_blacklist == 1

    # 4. 验证设备A的Token验证失败
    is_valid, reason = await session_service.validate_session(
        user_id=1,
        token_jti="old-device-jti"
    )
    assert is_valid is False
    assert "已在其他设备登录" in reason or "Token已被撤销" in reason
