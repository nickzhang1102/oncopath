"""单点登录会话管理服务测试"""
import pytest
import json
from datetime import datetime

from app.services.session_service import SessionService


@pytest.mark.asyncio
async def test_create_session_new_user(redis_client):
    """测试新用户创建会话"""
    session_service = SessionService(redis_client)

    result = await session_service.create_session(
        user_id=1,
        token_jti="test-jti-1",
        expires_in=3600
    )

    assert result is True

    # 验证会话已存储
    jti = await redis_client.get("session:user:1")
    assert jti == "test-jti-1"

    # 验证在线状态
    online_info = await redis_client.get("user:online:1")
    assert online_info is not None
    online_data = json.loads(online_info)
    assert online_data["jti"] == "test-jti-1"


@pytest.mark.asyncio
async def test_create_session_kick_old(redis_client):
    """测试踢下线旧会话"""
    session_service = SessionService(redis_client)

    # 创建第一个会话
    await session_service.create_session(
        user_id=1,
        token_jti="old-jti",
        expires_in=3600
    )

    # 创建第二个会话（应踢下线第一个）
    await session_service.create_session(
        user_id=1,
        token_jti="new-jti",
        expires_in=3600
    )

    # 验证旧会话在黑名单
    in_blacklist = await redis_client.exists("token:blacklist:old-jti")
    assert in_blacklist == 1

    # 验证新会话有效
    jti = await redis_client.get("session:user:1")
    assert jti == "new-jti"


@pytest.mark.asyncio
async def test_validate_session_valid(redis_client):
    """测试有效会话验证"""
    session_service = SessionService(redis_client)

    await session_service.create_session(
        user_id=1,
        token_jti="valid-jti",
        expires_in=3600
    )

    is_valid, reason = await session_service.validate_session(
        user_id=1,
        token_jti="valid-jti"
    )

    assert is_valid is True
    assert reason == "会话有效"


@pytest.mark.asyncio
async def test_validate_session_blacklisted(redis_client):
    """测试黑名单会话"""
    session_service = SessionService(redis_client)

    # 创建会话
    await session_service.create_session(
        user_id=1,
        token_jti="jti-1",
        expires_in=3600
    )

    # 加入黑名单
    await redis_client.setex("token:blacklist:jti-1", 3600, "1")

    is_valid, reason = await session_service.validate_session(
        user_id=1,
        token_jti="jti-1"
    )

    assert is_valid is False
    assert reason == "Token已被撤销"


@pytest.mark.asyncio
async def test_validate_session_another_device(redis_client):
    """测试在其他设备登录"""
    session_service = SessionService(redis_client)

    # 创建会话
    await session_service.create_session(
        user_id=1,
        token_jti="old-jti",
        expires_in=3600
    )

    # 模拟在其他设备登录
    await session_service.create_session(
        user_id=1,
        token_jti="new-jti",
        expires_in=3600
    )

    # 验证旧会话
    is_valid, reason = await session_service.validate_session(
        user_id=1,
        token_jti="old-jti"
    )

    assert is_valid is False
    assert reason == "Token已被撤销"


@pytest.mark.asyncio
async def test_validate_session_expired(redis_client):
    """测试会话过期"""
    session_service = SessionService(redis_client)

    # 创建会话
    await session_service.create_session(
        user_id=1,
        token_jti="expired-jti",
        expires_in=1  # 1秒后过期
    )

    # 等待过期
    import asyncio
    await asyncio.sleep(2)

    is_valid, reason = await session_service.validate_session(
        user_id=1,
        token_jti="expired-jti"
    )

    assert is_valid is False
    assert reason == "会话不存在或已过期"


@pytest.mark.asyncio
async def test_revoke_session(redis_client):
    """测试撤销会话"""
    session_service = SessionService(redis_client)

    await session_service.create_session(
        user_id=1,
        token_jti="jti-to-revoke",
        expires_in=3600
    )

    # 撤销会话
    await session_service.revoke_session(user_id=1)

    # 验证会话已删除
    jti = await redis_client.get("session:user:1")
    assert jti is None

    # 验证在黑名单
    in_blacklist = await redis_client.exists("token:blacklist:jti-to-revoke")
    assert in_blacklist == 1


@pytest.mark.asyncio
async def test_extend_session_ttl(redis_client):
    """测试延长会话TTL"""
    session_service = SessionService(redis_client)

    await session_service.create_session(
        user_id=1,
        token_jti="jti-to-extend",
        expires_in=3600
    )

    # 获取当前TTL
    ttl_before = await redis_client.ttl("session:user:1")

    # 延长TTL
    result = await session_service.extend_session_ttl(
        user_id=1,
        token_jti="jti-to-extend",
        additional_time=1800  # 延长30分钟
    )

    assert result is True

    # 验证TTL已延长
    ttl_after = await redis_client.ttl("session:user:1")
    assert ttl_after > ttl_before


@pytest.mark.asyncio
async def test_extend_session_ttl_wrong_jti(redis_client):
    """测试使用错误的jti延长会话"""
    session_service = SessionService(redis_client)

    await session_service.create_session(
        user_id=1,
        token_jti="correct-jti",
        expires_in=3600
    )

    # 尝试用错误的jti延长
    result = await session_service.extend_session_ttl(
        user_id=1,
        token_jti="wrong-jti",
        additional_time=1800
    )

    assert result is False


@pytest.mark.asyncio
async def test_get_session_info(redis_client):
    """测试获取会话信息"""
    session_service = SessionService(redis_client)

    await session_service.create_session(
        user_id=1,
        token_jti="info-jti",
        expires_in=3600,
        device_info={"ip": "127.0.0.1", "user_agent": "test"}
    )

    info = await session_service.get_session_info(user_id=1)

    assert info is not None
    assert info["jti"] == "info-jti"
    assert info["ttl"] > 0
    assert info["device_info"]["device"]["ip"] == "127.0.0.1"


@pytest.mark.asyncio
async def test_get_online_users(redis_client):
    """测试获取在线用户列表"""
    session_service = SessionService(redis_client)

    # 创建多个在线用户
    await session_service.create_session(
        user_id=1,
        token_jti="jti-1",
        expires_in=3600
    )
    await session_service.create_session(
        user_id=2,
        token_jti="jti-2",
        expires_in=3600
    )

    online_users = await session_service.get_online_users()

    assert len(online_users) == 2
    user_ids = [u["user_id"] for u in online_users]
    assert 1 in user_ids
    assert 2 in user_ids


@pytest.mark.asyncio
async def test_concurrent_login(redis_client):
    """测试并发登录场景"""
    session_service = SessionService(redis_client)

    # 模拟并发登录（两个设备同时登录）
    import asyncio

    async def login_device(device_id):
        jti = f"jti-device-{device_id}"
        await session_service.create_session(
            user_id=1,
            token_jti=jti,
            expires_in=3600
        )
        return jti

    # 并发执行
    results = await asyncio.gather(
        login_device(1),
        login_device(2)
    )

    # 验证只有一个会话是有效的
    is_valid_1, _ = await session_service.validate_session(user_id=1, token_jti=results[0])
    is_valid_2, _ = await session_service.validate_session(user_id=1, token_jti=results[1])

    # 其中一个应该失效（被踢下线）
    assert (is_valid_1 and not is_valid_2) or (not is_valid_1 and is_valid_2)
