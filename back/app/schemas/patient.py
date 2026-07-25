from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import Optional, List
from datetime import date, datetime


class PatientCreate(BaseModel):
    patient_name: str = Field(..., min_length=1, max_length=50)
    patient_phone: Optional[str] = None
    gender: Optional[str] = None  # male/female/unknown
    birth_date: Optional[date] = None
    id_card: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    medical_history: Optional[str] = None
    allergies: Optional[str] = None
    current_medications: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('birth_date', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        """将空字符串转为 None，避免 Pydantic 尝试解析空字符串为日期"""
        if v == '' or v is None:
            return None
        return v


class PatientUpdate(BaseModel):
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    id_card: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    medical_history: Optional[str] = None
    allergies: Optional[str] = None
    current_medications: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('birth_date', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class PatientResponse(BaseModel):
    """患者响应 — 敏感字段仅返回脱敏版本

    安全保障：model_validator 在序列化前强制脱敏，
    即使调用方忘记手动脱敏也不会泄露明文 PHI。
    """
    patient_id: int
    account_id: int
    patient_name: Optional[str] = None  # 脱敏后的姓名
    patient_phone: Optional[str] = None  # 脱敏后的电话
    gender: Optional[str]
    birth_date: Optional[date]
    id_card: Optional[str] = None  # 脱敏后的身份证
    emergency_contact: Optional[str] = None  # 脱敏后
    emergency_phone: Optional[str] = None  # 脱敏后
    medical_history: Optional[str]
    allergies: Optional[str]
    current_medications: Optional[str]
    notes: Optional[str]
    is_primary: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(
        from_attributes=True
    )

    @model_validator(mode='after')
    def force_desensitize(self) -> 'PatientResponse':
        """强制脱敏敏感字段，防止调用方遗漏"""
        from app.services.desensitization import desensitization_service

        if self.patient_name:
            self.patient_name = desensitization_service.mask_name(self.patient_name)
        if self.patient_phone:
            self.patient_phone = desensitization_service.mask_phone(self.patient_phone)
        if self.id_card:
            self.id_card = desensitization_service.mask_id_card(self.id_card)
        if self.emergency_contact:
            self.emergency_contact = desensitization_service.mask_name(self.emergency_contact)
        if self.emergency_phone:
            self.emergency_phone = desensitization_service.mask_phone(self.emergency_phone)
        return self


class PatientEditResponse(BaseModel):
    """患者编辑响应 — 敏感字段返回明文供编辑使用"""
    patient_id: int
    account_id: int
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    gender: Optional[str]
    birth_date: Optional[date]
    id_card: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    medical_history: Optional[str]
    allergies: Optional[str]
    current_medications: Optional[str]
    notes: Optional[str]
    is_primary: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(
        from_attributes=True
    )


class PatientListResponse(BaseModel):
    patient_id: int
    patient_name: Optional[str] = None  # 脱敏后的姓名
    gender: Optional[str]
    birth_date: Optional[date] = None
    age: Optional[int] = None
    is_primary: bool
    # 医疗摘要统计
    check_count: int = 0
    exam_count: int = 0
    record_count: int = 0
