"""记录概要摘要模型"""
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.time_utils import get_utc_now


class RecordSummary(Base):
    """记录概要摘要表"""
    __tablename__ = "record_summary"

    summary_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient.patient_id"), nullable=False, comment="患者ID")

    summary_type = Column(String(20), nullable=False, comment="概要类型: treatment/medication_record/status")
    period_start = Column(Date, nullable=False, comment="概要时段起始")
    period_end = Column(Date, nullable=False, comment="概要时段结束")
    summary_text = Column(Text, nullable=False, comment="概要内容")
    source = Column(String(20), nullable=False, default="rule_template", comment="来源: rule_template/llm_generated")
    status = Column(String(20), nullable=False, default="draft", comment="状态: draft/confirmed")
    source_record_count = Column(Integer, nullable=True, comment="生成时涵盖的原始记录数")

    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    patient = relationship("Patient", back_populates="record_summaries")

    __table_args__ = (
        UniqueConstraint('patient_id', 'summary_type', 'period_start', 'period_end',
                         name='uq_record_summary_patient_type_period'),
    )

    def to_dict(self):
        return {
            "summary_id": self.summary_id,
            "patient_id": self.patient_id,
            "summary_type": self.summary_type,
            "period_start": self.period_start.strftime("%Y-%m-%d") if self.period_start else None,
            "period_end": self.period_end.strftime("%Y-%m-%d") if self.period_end else None,
            "summary_text": self.summary_text,
            "source": self.source,
            "status": self.status,
            "source_record_count": self.source_record_count,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }