import pytest
import pytest_asyncio
import os
import logging
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
import redis.asyncio as redis
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Tests exercise endpoint behavior, not production request throttling.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

# 加载.env文件
load_dotenv()

from app.main import app
from app.core.database import get_db, Base
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.medical import MedicalCheck, MedicalExam, PathologyReport, MedicalRecord
from app.models.conversation import Conversation, LeaderSession
from app.models.timeline import TimelineEvent
from app.models.medical import MedicalIndex as StandardIndicator  # StandardIndicator已合并到MedicalIndex
from app.core.security import get_password_hash


def safe_password_hash(password: str) -> str:
    """安全地哈希密码（自动处理bcrypt长度限制）

    bcrypt限制密码长度为72字节，此函数自动截断以避免错误。

    Args:
        password: 原始密码字符串

    Returns:
        哈希后的密码字符串
    """
    return get_password_hash(password[:72])

# 测试数据库URL - 使用.env中的数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_NAME = os.getenv("DB_NAME", "medical_report")

# 使用独立的测试数据库（添加 _test 后缀）
TEST_DB_NAME = f"{DB_NAME}_test"
TEST_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TEST_DB_NAME}"

# 创建测试引擎 - 使用NullPool避免连接池问题
from sqlalchemy.pool import NullPool
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool  # 每次创建新连接，避免连接池复用问题
)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True, loop_scope="session")
async def setup_test_database():
    """自动创建/销毁测试数据库"""
    # 使用主数据库连接创建测试数据库
    admin_url = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT", poolclass=NullPool)

    async with admin_engine.connect() as conn:
        # 检查测试数据库是否已存在
        result = await conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{TEST_DB_NAME}'")
        )
        if not result.scalar():
            await conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
            logger.info(f"✓ 测试数据库 {TEST_DB_NAME} 已创建")

    await admin_engine.dispose()

    # 在测试数据库中创建表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # 清理：删除测试数据库
    async with admin_engine.connect() as conn:
        # 断开所有连接
        await conn.execute(text(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{TEST_DB_NAME}'
            AND pid <> pg_backend_pid()
        """))
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
        logger.info(f"✓ 测试数据库 {TEST_DB_NAME} 已删除")

    await admin_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """创建数据库会话（每个测试独立事务，测试后回滚）"""
    async with TestSessionLocal() as session:
        # 开始事务
        await session.begin()
        try:
            yield session
        finally:
            # 测试结束回滚事务
            await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """创建测试客户端"""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session):
    """创建测试用户（使用唯一用户名避免冲突）"""
    import uuid
    unique_username = f"testuser_{uuid.uuid4().hex[:8]}"

    user = LoginAccount(
        username=unique_username,
        password=safe_password_hash("testpass123"),
        account_name="测试用户",
        status="active"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user


@pytest_asyncio.fixture
async def auth_headers(client, test_user):
    """获取认证头"""
    response = await client.post("/api/v1/auth/login", json={
        "username": test_user.username,  # 使用test_user的实际用户名
        "password": "testpass123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def redis_client():
    """创建Redis测试客户端"""
    client = redis.from_url("redis://localhost:6379/15", decode_responses=True)
    try:
        yield client
    finally:
        # 清理测试数据
        await client.flushdb()
        await client.close()
