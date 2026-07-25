"""启动Celery Worker

启动Celery worker进程，处理异步任务。
"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """启动Celery worker"""
    try:
        from celery.bin.worker import worker
        from app.core.celery_app import celery_app

        logger.info("Starting Celery worker...")

        # 创建worker实例
        worker_app = worker(app=celery_app)

        # 启动worker
        worker_app.run(
            loglevel="info",
            concurrency=4,  # 并发进程数
            pool="prefork",  # 进程池
            queues=["default", "consultation", "reports"]  # 监听的队列
        )

    except ImportError as e:
        logger.error(f"Failed to import Celery: {e}")
        logger.error("Please install Celery: pip install celery==5.3.6")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start Celery worker: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()