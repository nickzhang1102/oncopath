"""通知服务 — 创建通知 + Redis 实时推送"""

import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.redis import redis_client
from app.models.notification import Notification
from app.schemas.user import NotificationResponse

logger = logging.getLogger(__name__)

NOTIFICATION_CHANNEL_PREFIX = "notifications:"


def _channel_name(account_id: int) -> str:
    return f"{NOTIFICATION_CHANNEL_PREFIX}{account_id}"


async def create_and_publish_notification(
    db: AsyncSession,
    account_id: int,
    type: str,
    title: str,
    content: Optional[str] = None,
    extra_data: Optional[dict] = None,
) -> Notification:
    """异步：创建通知记录 + Redis publish 推送"""
    notification = Notification(
        account_id=account_id,
        type=type,
        title=title,
        content=content,
        extra_data=extra_data,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    # 推送到 SSE
    try:
        payload = NotificationResponse.model_validate(notification).model_dump(mode="json")
        await redis_client.publish(_channel_name(account_id), json.dumps(payload, ensure_ascii=False))
    except Exception as e:
        logger.warning(f"通知推送失败 (account_id={account_id}): {e}")

    return notification


# ---- 同步版本（Celery 任务用）----

_sync_engine = None
_SyncSessionLocal = None


def _get_sync_session():
    global _sync_engine, _SyncSessionLocal
    if _sync_engine is None:
        db_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
        if not db_url.startswith("postgresql"):
            db_url = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        _sync_engine = create_engine(db_url)
        _SyncSessionLocal = sessionmaker(bind=_sync_engine)
    return _SyncSessionLocal()


def create_and_publish_notification_sync(
    account_id: int,
    type: str,
    title: str,
    content: Optional[str] = None,
    extra_data: Optional[dict] = None,
) -> Optional[Notification]:
    """同步：创建通知记录 + Redis publish 推送（Celery 任务用）"""
    import redis as sync_redis

    session = _get_sync_session()
    try:
        notification = Notification(
            account_id=account_id,
            type=type,
            title=title,
            content=content,
            extra_data=extra_data,
        )
        session.add(notification)
        session.commit()
        session.refresh(notification)

        # 同步 Redis publish
        try:
            payload = NotificationResponse.model_validate(notification).model_dump(mode="json")
            r = sync_redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD or None,
                decode_responses=True,
            )
            r.publish(_channel_name(account_id), json.dumps(payload, ensure_ascii=False))
            r.close()
        except Exception as e:
            logger.warning(f"通知推送失败 (account_id={account_id}, sync): {e}")

        return notification

    except Exception as e:
        session.rollback()
        logger.error(f"创建通知失败 (account_id={account_id}): {e}")
        return None
    finally:
        session.close()
