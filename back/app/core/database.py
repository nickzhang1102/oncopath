import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)


# 声明性基类 (SQLAlchemy 2.0 推荐方式)
class Base(DeclarativeBase):
    pass


# 创建异步引擎
if settings.DEBUG:
    # 开发环境：NullPool 避免连接复用问题
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=NullPool,
        future=True
    )
else:
    # 生产环境：使用连接池
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=AsyncAdaptedQueuePool,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
        connect_args={
            "timeout": 10,
            "command_timeout": 60,
            "server_settings": {
                "application_name": "oncopath-api",
                "tcp_keepalives_idle": "60",
                "tcp_keepalives_interval": "10",
                "tcp_keepalives_count": "5",
            },
        },
        future=True
    )

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# 导出会话工厂供后台任务使用
async_session_factory = AsyncSessionLocal


async def get_db():
    """获取数据库会话依赖"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """初始化数据库 (创建所有表)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
