from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import traceback
import asyncio
from sqlalchemy import text

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import engine, Base
from app.core.redis import redis_client
from app.core.rate_limit import limiter
from app.routers import api_router
from app.utils.datetime_encoder import UTCJSONResponse

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    # 初始化应用状态
    app.state.cache_loaded = False
    app.state.cache_error = None

    try:
        async with engine.begin() as conn:
            # 开发环境自动创建表 (生产环境使用Alembic)
            # await conn.run_sync(Base.metadata.create_all)
            pass
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")

    # 测试Redis连接
    try:
        await redis_client.ping()
        logger.info("✓ Redis连接成功")
    except Exception as e:
        logger.error(f"✗ Redis连接失败: {e}")

    # 启动时加载数据库中的活跃 LLM 配置到运行时（失败不阻断启动）
    try:
        from app.core.database import async_session_factory
        from app.services.llm_config_service import LLMConfigService
        async with async_session_factory() as session:
            group_count = await LLMConfigService.load_and_apply(session)
        if group_count:
            logger.info(f"✓ 已从数据库加载 LLM 配置（{group_count} 组）")
    except Exception as e:
        logger.warning(f"⚠ LLM 配置加载失败，使用环境变量默认值: {e}")

    # 预加载OCR标准库指标缓存
    async def load_indicator_cache():
        """后台加载标准库指标缓存"""
        try:
            from app.services.ocr.llm_ocr_parser import llm_ocr_parser
            await llm_ocr_parser._get_standard_indicators(None)
            logger.info("✓ 标准库指标缓存加载成功")
            return True
        except Exception as e:
            logger.warning(f"⚠ 标准库指标缓存加载失败: {e}")
            return False

    def on_cache_task_done(task: asyncio.Task):
        """后台任务完成回调"""
        if task.cancelled():
            logger.info("标准库指标缓存加载任务已取消")
            app.state.cache_error = "cancelled"
        elif task.exception():
            logger.error(f"标准库指标缓存加载异常: {task.exception()}")
            app.state.cache_error = str(task.exception())
        else:
            result = task.result()
            app.state.cache_loaded = result
            logger.info(f"标准库指标缓存加载完成，结果: {result}")

    cache_task = asyncio.create_task(load_indicator_cache())
    cache_task.add_done_callback(on_cache_task_done)
    # 持有引用防止 GC 回收
    app.state.cache_task = cache_task
    logger.info("标准库指标缓存正在后台加载中...")

    yield

    # 关闭时执行
    # 显式取消后台任务，避免 asyncio 警告和资源泄漏
    if not cache_task.done():
        cache_task.cancel()
        try:
            await cache_task
        except asyncio.CancelledError:
            logger.info("标准库指标缓存加载任务已取消")

    # 关闭 Playwright 浏览器实例
    try:
        from app.services.export_service import close_playwright_browser
        close_playwright_browser()
        logger.info("✓ Playwright Browser 已关闭")
    except Exception as e:
        logger.warning(f"关闭 Playwright Browser 失败: {e}")

    await engine.dispose()
    await redis_client.close()

app = FastAPI(
    title="医疗报告系统 API",
    description="Medical Report System API v2.0",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    # 全局应用 UTCJSONResponse：所有 datetime 字段自动序列化为
    # 带 Z 后缀的 ISO 8601 字符串，避免前端按本地时区误读导致 8 小时偏差
    default_response_class=UTCJSONResponse,
)

# 速率限制
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# 全局异常处理器 - 捕获所有未处理的异常
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器，记录详细错误信息但不泄露给客户端"""
    error_detail = {
        "error": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
        "path": str(request.url)
    }
    logger.error(f"Unhandled exception: {error_detail}")

    if settings.DEBUG:
        # DEBUG 模式下返回错误类型和过滤后的消息
        safe_message = _sanitize_error_message(str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": safe_message, "error_type": type(exc).__name__}
        )

    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试"}
    )


def _sanitize_error_message(message: str) -> str:
    """过滤异常消息中的敏感信息"""
    import re
    # 移除数据库连接字符串
    message = re.sub(
        r'postgresql(?:\+asyncpg)?://[^\s]+',
        '[DATABASE_URL_REDACTED]',
        message
    )
    # 移除 Redis 连接字符串
    message = re.sub(
        r'redis://[^\s]+',
        '[REDIS_URL_REDACTED]',
        message
    )
    # 移除 AMQP/Celery 连接字符串
    message = re.sub(
        r'amqp://[^\s]+',
        '[AMQP_URL_REDACTED]',
        message
    )
    # 移除文件路径（支持任意 Windows 盘符 + Unix 路径）
    message = re.sub(
        r'(?:[A-Za-z]:\\|/home/|/var/|/etc/|/tmp/)\S+',
        '[PATH_REDACTED]',
        message
    )
    # 移除 API 密钥模式
    message = re.sub(
        r'(?:api[_-]?key|token|secret|password|credential)["\s:=]+[\w\-]{8,}',
        '[CREDENTIAL_REDACTED]',
        message,
        flags=re.IGNORECASE
    )
    return message

# 注册路由
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
@app.get("/api/v1/health")
async def health_check():
    """Readiness check for the database-backed API."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        logger.warning("健康检查失败：数据库不可用")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "version": settings.APP_VERSION,
                "database_ready": False,
            },
        )

    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "database_ready": True,
        "cache_loaded": getattr(app.state, 'cache_loaded', False),
        "cache_error": getattr(app.state, 'cache_error', None)
    }

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "医疗报告系统 API v2.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }
