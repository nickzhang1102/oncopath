from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any
from datetime import date, datetime

from app.services.desensitization import desensitization_service


class DashboardAbnormalIndicator(BaseModel):
    """异常指标摘要项"""
    index_name: str
    index_value: Optional[str] = None
    index_unit: Optional[str] = None
    index_status: Optional[str] = None
    reference_value: Optional[str] = None
    medical_date: Optional[date] = None


class DashboardActiveMedication(BaseModel):
    """当前用药摘要项"""
    medication_name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    status: str


class DashboardTimelineEvent(BaseModel):
    """近期时间线事件摘要"""
    id: str
    source_type: str
    title: str
    event_date: date
    category: Optional[str] = None


class AdminUserStats(BaseModel):
    """管理后台-用户统计"""
    total: int = 0
    active: int = 0
    inactive: int = 0
    today_new: int = 0


class AdminConsultationStats(BaseModel):
    """管理后台-会诊统计"""
    total: int = 0
    completed: int = 0
    ongoing: int = 0
    failed: int = 0
    today_count: int = 0


class AdminIndexStats(BaseModel):
    """管理后台-指标库统计"""
    total: int = 0
    active: int = 0
    inactive: int = 0
    category_count: int = 0


class AdminSystemStats(BaseModel):
    """管理后台-系统概要"""
    total_patients: int = 0


class AdminDailyTrend(BaseModel):
    """管理后台-每日趋势"""
    date: str
    new_users: int = 0
    consultations: int = 0


class AdminStatsResponse(BaseModel):
    """管理后台仪表盘聚合数据"""
    users: AdminUserStats = AdminUserStats()
    consultations: AdminConsultationStats = AdminConsultationStats()
    indices: AdminIndexStats = AdminIndexStats()
    system: AdminSystemStats = AdminSystemStats()
    daily_trend: list[AdminDailyTrend] = []


class DashboardResponse(BaseModel):
    """首页仪表盘聚合数据"""
    # 患者信息
    patient_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    medical_history: Optional[str] = None
    id_card: Optional[str] = None
    patient_phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    allergies: Optional[str] = None

    # 当前用药
    active_medication_count: int = 0
    active_medications: List[DashboardActiveMedication] = []

    # 异常指标
    abnormal_indicator_count: int = 0
    abnormal_indicators: List[DashboardAbnormalIndicator] = []

    # 时间线摘要
    recent_events: List[DashboardTimelineEvent] = []

    # 统计数据
    check_count: int = 0
    exam_count: int = 0
    pathology_count: int = 0
    timeline_event_count: int = 0
    medication_total: int = 0

    # 待办提醒
    pending_review_count: int = 0
    ongoing_consultation_count: int = 0
    pending_reminder_count: int = 0

    # 日期范围
    earliest_date: Optional[str] = None
    latest_date: Optional[str] = None

    @model_validator(mode='after')
    def force_desensitize(self):
        """强制脱敏 PHI 字段（防御纵深，API 层已脱敏，此为二次保障）"""
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
