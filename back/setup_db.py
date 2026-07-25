"""
数据库初始化脚本
创建数据库并执行迁移
"""
import asyncio
import sys
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "medical_report")

async def create_database():
    """创建数据库（如果不存在）"""
    # 连接到postgres默认数据库
    postgres_url = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres"
    engine = create_async_engine(postgres_url, isolation_level="AUTOCOMMIT")

    try:
        async with engine.connect() as conn:
            # 检查数据库是否存在
            result = await conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
            )
            exists = result.scalar() is not None

            if not exists:
                print(f"Creating database: {DB_NAME}")
                await conn.execute(text(f"CREATE DATABASE {DB_NAME}"))
                print(f"Database {DB_NAME} created successfully")
            else:
                print(f"Database {DB_NAME} already exists")

        # 连接到目标数据库并创建扩展
        db_url = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        db_engine = create_async_engine(db_url, isolation_level="AUTOCOMMIT")

        async with db_engine.connect() as conn:
            # 创建pgvector扩展
            print("Creating pgvector extension...")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            print("pgvector extension created successfully")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("=" * 60)
    print("Medical Report System - Database Initialization")
    print("=" * 60)
    asyncio.run(create_database())
    print("\nDatabase setup completed!")
    print("\nNext step: Run 'alembic upgrade head' to execute migrations")
