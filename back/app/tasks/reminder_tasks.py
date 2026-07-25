"""随访提醒 Celery 定时任务

每日检查待发送提醒，创建应用内通知，过期标记
"""
import logging
from datetime import date, timedelta

from celery import shared_task
from sqlalchemy import create_engine, select, and_
from sqlalchemy.orm import sessionmaker

from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.notification_service import create_and_publish_notification_sync

logger = logging.getLogger(__name__)

# 同步数据库连接
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


@shared_task(name="check_follow_up_reminders")
def check_follow_up_reminders():
    """检查并处理随访提醒

    - 提前7天/3天/当天的 pending 提醒 → 发送通知，状态改为 sent
    - 超过提醒日期7天未确认的 → 标记 expired
    """
    from app.models.follow_up import FollowUpReminder

    today = date.today()
    notify_dates = [today, today + timedelta(days=3), today + timedelta(days=7)]

    session = _get_sync_session()
    try:
        # 1. 发送即将到期的提醒通知
        reminders = session.execute(
            select(FollowUpReminder).where(
                FollowUpReminder.status == "pending",
                FollowUpReminder.reminder_date.in_(notify_dates),
            )
        ).scalars().all()

        for reminder in reminders:
            days_left = (reminder.reminder_date - today).days
            if days_left == 0:
                msg = f"今天需要复查：{reminder.title}"
            elif days_left == 3:
                msg = f"3天后需要复查：{reminder.title}"
            else:
                msg = f"7天后需要复查：{reminder.title}"

            # 创建通知 + 实时推送
            create_and_publish_notification_sync(
                account_id=reminder.account_id,
                title="随访提醒",
                content=msg,
                type="reminder",
            )
            reminder.status = "sent"

        session.commit()
        if reminders:
            logger.info(f"已发送 {len(reminders)} 条随访提醒通知")

        # 2. 过期标记
        expired_date = today - timedelta(days=7)
        expired = session.execute(
            select(FollowUpReminder).where(
                FollowUpReminder.status.in_(["pending", "sent"]),
                FollowUpReminder.reminder_date < expired_date,
            )
        ).scalars().all()

        for reminder in expired:
            reminder.status = "expired"

        session.commit()
        if expired:
            logger.info(f"已标记 {len(expired)} 条过期提醒")

    except Exception as e:
        session.rollback()
        logger.error(f"随访提醒检查失败: {e}")
    finally:
        session.close()