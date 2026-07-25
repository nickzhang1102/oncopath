"""随访提醒 Pydantic Schemas"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import date, datetime

from app.utils.time_utils import get_utc_now


class FollowUpReminderCreate(BaseModel):
    """创建随访提醒"""
    patient_id: int = Field(..., description="患者ID")
    title: str = Field(..., max_length=200, description="提醒标题")
    description: Optional[str] = Field(None, description="描述")
    reminder_date: date = Field(..., description="提醒日期")
    source_type: Optional[str] = Field(None, description="来源: manual/interpretation/consultation")
    source_id: Optional[int] = Field(None, description="关联来源ID")

    @field_validator('reminder_date')
    @classmethod
    def validate_reminder_date(cls, v: date) -> date:
        if v < get_utc_now().date():
            raise ValueError('提醒日期不能是过去日期')
        return v


class FollowUpReminderUpdate(BaseModel):
    """更新随访提醒"""
    title: Optional[str] = Field(None, max_length=200, description="提醒标题")
    description: Optional[str] = Field(None, description="描述")
    reminder_date: Optional[date] = Field(None, description="提醒日期")


class FollowUpReminderResponse(BaseModel):
    """随访提醒响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    account_id: int
    title: str
    description: Optional[str] = None
    reminder_date: date
    status: str = "pending"
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FollowUpReminderListResponse(BaseModel):
    """随访提醒分页响应"""
    items: List[FollowUpReminderResponse]
    total: int