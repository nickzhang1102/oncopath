"""服药打卡 Pydantic Schemas"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime


class MedicationLogCreate(BaseModel):
    medication_id: int
    scheduled_date: date
    scheduled_time: Optional[str] = None
    time_slot: Optional[str] = Field(None, description="时段: morning/afternoon/evening/bedtime")
    status: str = "taken"  # taken/skipped/missed
    notes: Optional[str] = None


class MedicationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    medication_id: int
    patient_id: int
    scheduled_date: date
    scheduled_time: Optional[str]
    time_slot: Optional[str]
    status: str
    actual_time: Optional[datetime]
    notes: Optional[str]


class AdherenceStats(BaseModel):
    medication_id: int
    medication_name: str
    total_slots: int
    taken_slots: int
    skipped_slots: int
    missed_slots: int
    unrecorded_slots: int
    adherence_rate: float       # 已记录中的服药率 = taken / recorded_slots
    effective_adherence: float  # 综合依从率 = taken / total_slots（含未记录项）
    recording_rate: float       # 记录率 = recorded_slots / total_slots


class TodayTaskSlot(BaseModel):
    time_slot: Optional[str]
    status: Optional[str]
    logged: bool


class TodayTask(BaseModel):
    medication_id: int
    medication_name: str
    dosage: Optional[str]
    frequency: Optional[str]
    category: Optional[str]
    slots: List[TodayTaskSlot]
    logged: bool  # 至少一个 slot 已打卡
