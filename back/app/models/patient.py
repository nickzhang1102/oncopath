import logging

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.time_utils import get_utc_now

logger = logging.getLogger(__name__)


class Patient(Base):
    """患者信息表"""
    __tablename__ = "patient"

    patient_id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("login_account.account_id"), nullable=False)
    patient_name = Column(String(200), nullable=False, comment="患者姓名（加密存储）")
    patient_phone = Column(String(200), nullable=True, comment="患者电话（加密存储）")
    gender = Column(String(10), nullable=True, comment="性别: male/female/unknown")
    birth_date = Column(Date, nullable=True, comment="出生日期")
    id_card = Column(String(200), nullable=True, comment="身份证号（加密存储）")
    id_card_hash = Column(String(64), nullable=True, unique=True, index=True, comment="身份证哈希索引（查重用）")
    emergency_contact = Column(String(200), nullable=True, comment="紧急联系人（加密存储）")
    emergency_phone = Column(String(200), nullable=True, comment="紧急联系电话（加密存储）")
    medical_history = Column(Text, nullable=True, comment="既往病史")
    allergies = Column(Text, nullable=True, comment="过敏史")
    current_medications = Column(Text, nullable=True, comment="当前用药")
    notes = Column(Text, nullable=True, comment="备注")
    is_primary = Column(Boolean, default=False, comment="是否主患者")
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # 关系
    account = relationship("LoginAccount", back_populates="patients")
    medical_checks = relationship("MedicalCheck", back_populates="patient", cascade="all, delete-orphan")
    medical_exams = relationship("MedicalExam", back_populates="patient", cascade="all, delete-orphan")
    pathology_reports = relationship("PathologyReport", back_populates="patient", cascade="all, delete-orphan")
    medical_records = relationship("MedicalRecord", back_populates="patient", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="patient", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="patient", cascade="all, delete-orphan")
    prompt_configs = relationship("PromptConfig", back_populates="patient", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="patient", cascade="all, delete-orphan")
    image_reports = relationship("ImageReport", back_populates="patient", cascade="all, delete-orphan")
    medication_logs = relationship("MedicationLog", back_populates="patient", cascade="all, delete-orphan")
    record_summaries = relationship("RecordSummary", back_populates="patient", cascade="all, delete-orphan")

    def encrypt_sensitive_fields(self):
        """写入前加密敏感字段（先算哈希再加密）"""
        from app.services.encryption_service import encryption_service
        # 先计算身份证哈希索引（需在加密前用明文计算）
        if self.id_card:
            self.id_card_hash = encryption_service.hash_for_index(self.id_card)
        self.patient_name = encryption_service.encrypt(self.patient_name)
        self.patient_phone = encryption_service.encrypt(self.patient_phone)
        self.id_card = encryption_service.encrypt(self.id_card)
        self.emergency_contact = encryption_service.encrypt(self.emergency_contact)
        self.emergency_phone = encryption_service.encrypt(self.emergency_phone)

    def decrypt_sensitive_fields(self):
        """读取后解密敏感字段，单个字段解密失败时保留密文并记录警告"""
        from app.services.encryption_service import encryption_service
        sensitive_fields = [
            'patient_name', 'patient_phone', 'id_card',
            'emergency_contact', 'emergency_phone'
        ]
        for field in sensitive_fields:
            ciphertext = getattr(self, field)
            if not ciphertext:
                continue
            try:
                setattr(self, field, encryption_service.decrypt(ciphertext))
            except ValueError as e:
                logger.warning(
                    f"PHI 字段解密失败，保留密文: field={field}, "
                    f"patient_id={self.patient_id}, error={e}"
                )

    def to_dict(self, decrypt: bool = True) -> dict:
        """转换为字典

        Args:
            decrypt: 是否先解密敏感字段再返回（默认 True）。
                     传 False 时返回原始 ORM 值（可能是密文）。

        注意：此方法不会修改 ORM 对象状态，解密仅作用于返回的字典。
        """
        data = {
            "patient_id": self.patient_id,
            "account_id": self.account_id,
            "patient_name": self.patient_name,
            "patient_phone": self.patient_phone,
            "gender": self.gender,
            "birth_date": self.birth_date,
            "id_card": self.id_card,
            "emergency_contact": self.emergency_contact,
            "emergency_phone": self.emergency_phone,
            "medical_history": self.medical_history,
            "allergies": self.allergies,
            "current_medications": self.current_medications,
            "notes": self.notes,
            "is_primary": self.is_primary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if decrypt:
            data = self._decrypt_dict_fields(data)
        return data

    def _decrypt_dict_fields(self, data: dict) -> dict:
        """解密字典中的敏感字段，不修改 ORM 对象状态"""
        from app.services.encryption_service import encryption_service
        encrypted_fields = ["patient_name", "patient_phone", "id_card",
                            "emergency_contact", "emergency_phone"]
        result = dict(data)
        for field in encrypted_fields:
            value = result.get(field)
            if value and isinstance(value, str):
                try:
                    result[field] = encryption_service.decrypt(value)
                except ValueError:
                    pass  # 保留密文
        return result
