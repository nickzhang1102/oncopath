"""Celery application configuration for async tasks."""
from celery import Celery
from app.core.config import settings

# 创建Celery应用
celery_app = Celery(
    "medical_report",
    broker=f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
    backend=f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
)

# Celery配置
celery_app.conf.update(
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,

    # 任务结果配置
    result_expires=3600,  # 结果保留1小时

    # Worker配置
    worker_prefetch_multiplier=1,  # 每次只取1个任务
    worker_max_tasks_per_child=100,  # 每个worker处理100个任务后重启
)

# 开发环境：任务同步执行（跳过 Redis broker）
if settings.DEBUG:
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )

# 自动发现任务
celery_app.autodiscover_tasks(["app.tasks"])
