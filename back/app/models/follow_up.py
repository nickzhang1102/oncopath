"""随访提醒模型"""
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.time_utils import get_utc_now


class FollowUpReminder(Base):
    """随访提醒表"""
    __tablename__ = "follow_up_reminder"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient.patient_id"), nullable=False)
    account_id = Column(Integer, ForeignKey("login_account.account_id"), nullable=False)

    title = Column(String(200), nullable=False, comment="提醒标题")
    description = Column(Text, nullable=True, comment="描述")
    reminder_date = Column(Date, nullable=False, comment="提醒日期")

    # 状态: pending -> sent -> confirmed / expired
    status = Column(String(20), default="pending", comment="状态: pending/sent/confirmed/expired")

    # 来源
    source_type = Column(String(30), nullable=True, comment="来源: manual/interpretation/consultation")
    source_id = Column(Integer, nullable=True, comment="关联来源ID")

    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # 关系
    patient = relationship("Patient", back_populates="follow_up_reminders")
    account = relationship("LoginAccount", back_populates="follow_up_reminders")

    __table_args__ = (
        Index('idx_follow_up_patient_status', 'patient_id', 'status'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "account_id": self.account_id,
            "title": self.title,
            "description": self.description,
            "reminder_date": self.reminder_date.isoformat() if self.reminder_date else None,
            "status": self.status,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }