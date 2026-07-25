"""用药记录 Pydantic Schemas"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


class MedicationStatus(str, Enum):
    """用药状态"""
    ACTIVE = "active"
    DISCONTINUED = "discontinued"
    COMPLETED = "completed"


class MedicationSource(str, Enum):
    """用药来源"""
    MANUAL = "manual"
    OCR = "ocr"
    PRESCRIPTION = "prescription"


class MedicationCreate(BaseModel):
    """创建用药记录"""
    patient_id: int = Field(..., description="患者ID")
    medication_name: str = Field(..., max_length=200, description="药品名称")
    generic_name: Optional[str] = Field(None, max_length=200, description="通用名")
    category: Optional[str] = Field(None, max_length=50, description="分类: 化疗/靶向/免疫/支持/止痛/其他")
    dosage: Optional[str] = Field(None, max_length=100, description="剂量(如: 5mg)")
    frequency: Optional[str] = Field(None, max_length=100, description="用药频率(如: 每日2次)")
    route: Optional[str] = Field(None, max_length=50, description="给药途径(如: 口服/静脉)")
    duration: Optional[str] = Field(None, max_length=100, description="用药时长(如: 14天)")
    start_date: date = Field(..., description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期(NULL=持续用药)")
    is_ongoing: bool = Field(True, description="是否持续用药中")
    prescriber: Optional[str] = Field(None, max_length=100, description="开药医生")
    hospital: Optional[str] = Field(None, max_length=100, description="开药医院")
    source: MedicationSource = Field(MedicationSource.MANUAL, description="来源")
    status: MedicationStatus = Field(MedicationStatus.ACTIVE, description="状态")
    notes: Optional[str] = Field(None, description="备注")
    side_effects: Optional[str] = Field(None, description="副作用记录")

    @field_validator("end_date", mode="before")
    @classmethod
    def empty_date_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v


class MedicationUpdate(BaseModel):
    """更新用药记录"""
    medication_name: Optional[str] = Field(None, max_length=200, description="药品名称")
    generic_name: Optional[str] = Field(None, max_length=200, description="通用名")
    category: Optional[str] = Field(None, max_length=50, description="分类")
    dosage: Optional[str] = Field(None, max_length=100, description="剂量")
    frequency: Optional[str] = Field(None, max_length=100, description="用药频率")
    route: Optional[str] = Field(None, max_length=50, description="给药途径")
    duration: Optional[str] = Field(None, max_length=100, description="用药时长")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    is_ongoing: Optional[bool] = Field(None, description="是否持续用药中")
    prescriber: Optional[str] = Field(None, max_length=100, description="开药医生")
    hospital: Optional[str] = Field(None, max_length=100, description="开药医院")
    status: Optional[MedicationStatus] = Field(None, description="状态")
    notes: Optional[str] = Field(None, description="备注")
    side_effects: Optional[str] = Field(None, description="副作用记录")

    @field_validator("end_date", mode="before")
    @classmethod
    def empty_date_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v


class MedicationResponse(BaseModel):
    """用药记录响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    account_id: int
    medication_name: str
    generic_name: Optional[str] = None
    category: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    duration: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    is_ongoing: bool = True
    prescriber: Optional[str] = None
    hospital: Optional[str] = None
    source: str = "manual"
    status: str = "active"
    notes: Optional[str] = None
    side_effects: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MedicationListResponse(BaseModel):
    """用药记录列表响应"""
    items: List[MedicationResponse]
    total: int
    active_count: int = 0
