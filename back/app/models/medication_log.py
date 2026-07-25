"""Medication log model"""
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.utils.time_utils import get_utc_now

class MedicationLog(Base):
    __tablename__ = "medication_log"
    id = Column(Integer, primary_key=True, index=True)
    medication_id = Column(Integer, ForeignKey("medications.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patient.patient_id"), nullable=False)
    account_id = Column(Integer, ForeignKey("login_account.account_id"), nullable=False, index=True)
    scheduled_date = Column(Date, nullable=False)
    scheduled_time = Column(String(50), nullable=True)
    time_slot = Column(String(20), nullable=True, comment="时段: morning/afternoon/evening/bedtime")
    status = Column(String(20), default="pending")
    actual_time = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # 关系
    medication = relationship("Medication", back_populates="logs")
    patient = relationship("Patient", back_populates="medication_logs")
    account = relationship("LoginAccount", back_populates="medication_logs")

    __table_args__ = (
        Index('ix_medication_log_med_date', 'medication_id', 'scheduled_date'),
        Index('ix_medication_log_patient_date', 'patient_id', 'scheduled_date'),
        Index('ix_medication_log_med_date_slot', 'medication_id', 'scheduled_date', 'time_slot'),
    )
