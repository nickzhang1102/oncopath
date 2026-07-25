from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Boolean, JSON, Index
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.time_utils import get_utc_now


class TimelineEvent(Base):
    """时间线事件表"""
    __tablename__ = "timeline_events"

    event_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient.patient_id"), nullable=False, index=True)
    event_type = Column(String(20), nullable=False, comment="事件类型: medical/life")
    category = Column(String(50), nullable=False, comment="分类: surgery/chemotherapy/diagnosis/mood/etc")
    event_date = Column(Date, nullable=False, comment="事件日期")
    title = Column(String(100), nullable=False, comment="标题")
    description = Column(Text, nullable=True, comment="描述")
    icon_type = Column(String(50), nullable=True, comment="图标类型")
    color_theme = Column(String(20), nullable=True, comment="颜色主题")
    is_private = Column(Boolean, default=False, comment="是否私密")
    related_report_id = Column(Integer, nullable=True, comment="关联报告ID")
    related_indicators = Column(JSON, nullable=True, comment="关联指标ID列表")
    medical_details = Column(JSON, nullable=True, comment="医疗事件详情")
    life_details = Column(JSON, nullable=True, comment="生活事件详情")
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # 关系
    patient = relationship("Patient", back_populates="timeline_events")

    __table_args__ = (
        Index('ix_timeline_events_patient_date', 'patient_id', 'event_date'),
    )
