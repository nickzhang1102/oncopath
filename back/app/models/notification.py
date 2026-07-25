from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.time_utils import get_utc_now


class Notification(Base):
    """用户通知表"""
    __tablename__ = "notification"

    notification_id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("login_account.account_id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False, comment="通知类型: system/consultation/report/reminder")
    title = Column(String(200), nullable=False, comment="标题")
    content = Column(Text, nullable=True, comment="内容")
    is_read = Column(Boolean, default=False, comment="是否已读")
    extra_data = Column(JSON, nullable=True, comment="额外数据")
    created_at = Column(DateTime, default=get_utc_now)

    # 关系
    account = relationship("LoginAccount", back_populates="notifications")

    __table_args__ = (
        Index('idx_notification_account_read', 'account_id', 'is_read'),
    )
