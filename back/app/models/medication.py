"""用药记录模型"""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Numeric, Boolean, Index
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.time_utils import get_utc_now


class Medication(Base):
    """用药记录表"""
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient.patient_id"), nullable=False, comment="患者ID")
    account_id = Column(Integer, ForeignKey("login_account.account_id"), nullable=False, comment="账号ID")

    # 药物信息
    medication_name = Column(String(200), nullable=False, comment="药品名称")
    generic_name = Column(String(200), nullable=True, comment="通用名")
    category = Column(String(50), nullable=True, comment="分类: 化疗/靶向/免疫/支持/止痛/其他")
    dosage = Column(String(100), nullable=True, comment="剂量(如: 5mg)")
    frequency = Column(String(100), nullable=True, comment="用药频率(如: 每日2次)")
    route = Column(String(50), nullable=True, comment="给药途径(如: 口服/静脉)")
    duration = Column(String(100), nullable=True, comment="用药时长(如: 14天)")

    # 时间范围
    start_date = Column(Date, nullable=False, comment="开始日期")
    end_date = Column(Date, nullable=True, comment="结束日期(NULL=持续用药)")
    is_ongoing = Column(Boolean, default=True, comment="是否持续用药中")

    # 来源与状态
    prescriber = Column(String(100), nullable=True, comment="开药医生")
    hospital = Column(String(100), nullable=True, comment="开药医院")
    source = Column(String(20), default="manual", comment="来源: manual/ocr/prescription")
    status = Column(String(20), default="active", comment="状态: active/discontinued/completed")

    # 备注
    notes = Column(Text, nullable=True, comment="备注")
    side_effects = Column(Text, nullable=True, comment="副作用记录")

    # 时间戳
    created_at = Column(DateTime, default=get_utc_now, comment="创建时间")
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, comment="更新时间")

    # 索引
    __table_args__ = (
        Index('idx_medications_patient_status', 'patient_id', 'status'),
        Index('idx_medications_account', 'account_id'),
        Index('idx_medications_start_date', 'start_date'),
    )

    # 关系
    patient = relationship("Patient", back_populates="medications")
    account = relationship("LoginAccount", back_populates="medications")
    logs = relationship("MedicationLog", back_populates="medication", cascade="all, delete-orphan")
