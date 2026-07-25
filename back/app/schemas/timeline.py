from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import date, datetime


class StatusScore(BaseModel):
    """单个状态类型的评分"""
    score: int = Field(..., ge=0, le=10)
    max_score: int = Field(default=10, ge=1, le=10)


class StoolStatus(BaseModel):
    """大便状态"""
    status: str = Field(default="normal", description="正常normal/稀便loose/便秘constipation")
    memo: Optional[str] = None


class DailyStatusDetails(BaseModel):
    """每日状态详情 - 包含所有状态类型"""
    # 各状态评分
    mood: Optional[StatusScore] = None
    pain: Optional[StatusScore] = None
    sleep: Optional[StatusScore] = None
    diet: Optional[StatusScore] = None
    stool: Optional[StoolStatus] = None
    # 整体备注
    general_memo: Optional[str] = None
    # 备忘录项目（保留原有功能）
    memo_items: Optional[List[Dict[str, Any]]] = None


class TimelineEventBase(BaseModel):
    event_type: str = Field(..., pattern="^(medical|life)$")  # medical, life
    category: str  # surgery, chemotherapy, diagnosis, mood, etc.
    event_date: date
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    icon_type: Optional[str] = None
    color_theme: Optional[str] = None
    is_private: bool = False

class TimelineEventCreate(TimelineEventBase):
    patient_id: int
    related_report_id: Optional[int] = None
    related_indicators: Optional[List[int]] = None
    medical_details: Optional[dict] = None
    life_details: Optional[dict] = None

class TimelineEventUpdate(BaseModel):
    event_type: Optional[str] = None
    category: Optional[str] = None
    event_date: Optional[date] = None
    title: Optional[str] = None
    description: Optional[str] = None
    icon_type: Optional[str] = None
    color_theme: Optional[str] = None
    is_private: Optional[bool] = None
    medical_details: Optional[dict] = None
    life_details: Optional[dict] = None

    @field_validator('event_date', mode='before')
    @classmethod
    def empty_date_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v

class TimelineEventResponse(TimelineEventBase):
    event_id: int
    patient_id: int
    related_report_id: Optional[int]
    related_indicators: Optional[List[int]]
    medical_details: Optional[dict] = None
    life_details: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(
        from_attributes=True
    )

class TimelineQuery(BaseModel):
    patient_id: int
    event_type: Optional[str] = None
    category: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    include_private: bool = True
    limit: int = 100

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def empty_date_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v

class TimelineStats(BaseModel):
    total_events: int
    medical_events: int
    life_events: int
    categories: dict
    date_range: dict


# ========== 统一时间线（聚合多来源） ==========

class UnifiedTimelineQuery(BaseModel):
    """统一时间线查询"""
    patient_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    offset: int = Field(default=0, ge=0, description="偏移量")
    limit: int = Field(default=50, ge=1, le=200)
    # 按来源类型过滤，可选值: timeline_event, medical_check, medical_exam, pathology_report, medication
    source_types: Optional[List[str]] = None

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def empty_date_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class UnifiedTimelineItem(BaseModel):
    """统一时间线条目 -- 所有来源的数据都映射到此模型"""
    id: str                           # 复合ID: "{source_type}:{original_id}"
    source_type: str                  # timeline_event | medical_check | medical_exam | pathology_report
    source_id: int                    # 原始表中的主键
    event_date: date
    title: str
    subtitle: Optional[str] = None   # 副标题: 医院名等
    description: Optional[str] = None
    category: Optional[str] = None   # 来源表的分类字段
    icon: Optional[str] = None       # 前端渲染用图标名
    color: Optional[str] = None      # 前端渲染用颜色
    extra: Optional[dict] = None     # 来源特有的额外数据
    created_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True
    )


class UnifiedTimelineStats(BaseModel):
    """统一时间线统计"""
    total: int
    by_source: Dict[str, int]        # {"timeline_event": 15, "medical_check": 8, ...}
    date_range: Dict[str, Optional[str]]
