#!/bin/bash
set -e

# Only the primary backend container owns schema and seed initialization. Worker
# containers still wait for the database, but must not race that initialization.
RUN_DB_MIGRATIONS="${RUN_DB_MIGRATIONS:-true}"
case "${RUN_DB_MIGRATIONS}" in
    true|TRUE|1|yes|YES)
        RUN_DB_MIGRATIONS=true
        ;;
    false|FALSE|0|no|NO)
        RUN_DB_MIGRATIONS=false
        ;;
    *)
        echo "[entrypoint] RUN_DB_MIGRATIONS must be true or false" >&2
        exit 1
        ;;
esac

# ============================================================
# 1. 修复 storage 目录权限（named volume 首次创建时可能属于 root）
# ============================================================
if [ -d "/app/storage" ]; then
    chown -R appuser:appuser /app/storage
fi

# 确保 storage 子目录存在
mkdir -p /app/storage/images /app/storage/thumbnails /app/storage/documents /app/storage/pathology
chown -R appuser:appuser /app/storage

# 修复 cache 目录权限
if [ -d "/app/.cache" ]; then
    chown -R appuser:appuser /app/.cache
fi

# ============================================================
# 2. 数据库初始化（等 PostgreSQL 就绪 → 自动建表/迁移/种子数据）
# ============================================================
# 先单独加载配置：SECRET_KEY / ENCRYPTION_KEY 等校验失败时立即报错退出，
# 避免配置异常被下方重试循环掩盖为"数据库未就绪"，误导排障。
if ! python -c "from app.core.config import settings" 2> /tmp/config_err; then
    echo "[entrypoint] 配置校验失败，拒绝启动：" >&2
    cat /tmp/config_err >&2
    exit 1
fi

echo "[entrypoint] 等待数据库就绪..."

DB_READY=false
for i in $(seq 1 30); do
    if python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
async def check():
    e = create_async_engine(settings.DATABASE_URL)
    async with e.connect() as c:
        await c.execute(__import__('sqlalchemy').text('SELECT 1'))
    await e.dispose()
asyncio.run(check())
" 2>/dev/null; then
        DB_READY=true
        break
    fi
    echo "[entrypoint] 数据库未就绪，${i}/30 秒后重试..."
    sleep 1
done

if [ "$DB_READY" = false ]; then
    echo "[entrypoint] 30 秒后数据库仍未就绪，拒绝启动未初始化的服务" >&2
    exit 1
else
    if [ "$RUN_DB_MIGRATIONS" = true ]; then
        echo "[entrypoint] 数据库已就绪，执行 schema 迁移..."
        alembic -c /app/alembic.ini upgrade head
        echo "[entrypoint] ✅ 数据库迁移完成"

        echo "[entrypoint] 初始化幂等种子数据..."
        python scripts/init_fresh_db.py
        echo "[entrypoint] ✅ 种子数据初始化完成"
    else
        echo "[entrypoint] 数据库已就绪，跳过 schema 迁移和种子初始化（RUN_DB_MIGRATIONS=false）"
    fi
fi

# ============================================================
# 3. 切换到 appuser 执行原始命令（uvicorn）
# ============================================================
exec gosu appuser "$@"
