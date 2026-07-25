from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ConsultationStatus(str, Enum):
    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


# ========== 查询相关 ==========

class ConsultationQuery(BaseModel):
    """会诊查询请求"""
    patient_id: Optional[int] = None
    status: Optional[ConsultationStatus] = None
    limit: int = 20
    offset: int = 0


class ConversationListResponse(BaseModel):
    """会诊列表响应（基于 Conversation 新模型）"""
    id: int
    patient_id: Optional[int] = None
    category: Optional[str] = None
    status: ConsultationStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 关联 LeaderSession 的摘要信息
    leader_session_id: Optional[int] = None
    state: Optional[str] = None
    assessment_score: Optional[int] = None
    risk_level: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ========== 新状态机模式相关 Schema ==========

class ConsultationMessageResponse(BaseModel):
    """会诊消息响应（对齐 LeaderMessage 新模型）"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    leader_session_id: int
    message_type: str
    content: Optional[dict] = None
    sequence_number: int
    created_at: Optional[datetime] = None


class ConsultationAgentResultResponse(BaseModel):
    """会诊专家结果响应（对齐 LeaderAgentResult 新模型）"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    leader_session_id: int
    agent_id: str
    agent_name: str
    status: str
    content: Optional[str] = None
    error: Optional[str] = None
    sequence_number: int
    created_at: Optional[datetime] = None


class QuestionAnswer(BaseModel):
    """追问回答子项"""
    question_id: str
    text: str


class AnswerQuestionsRequest(BaseModel):
    """回答追问请求"""
    answers: List[QuestionAnswer]


class StartConsultationRequestV2(BaseModel):
    """启动会诊请求（状态机模式）"""
    patient_id: int
    user_message: Optional[str] = Field(None, max_length=5000, description="用户附加说明")
    selected_experts: Optional[List[str]] = None
    file_ids: Optional[List[int]] = None


class ConsultationReportBrief(BaseModel):
    """会诊报告摘要（会话详情内嵌，对齐 LeaderFinalReport）"""
    model_config = ConfigDict(from_attributes=True)
    content: Optional[str] = None
    expert_count: int = 0
    generated_at: Optional[datetime] = None


class ConsultationSessionDetailResponseV2(BaseModel):
    """会诊会话详情（状态机模式）— 对齐新数据结构

    字段变更（vs 旧版）：
    - 删除 scene_type（新模型无此字段）
    - selected_experts 类型从 Optional[list] 改为 Optional[str]（逗号分隔字符串）
    - messages 和 agent_results 适配新模型字段
    """
    model_config = ConfigDict(from_attributes=True)
    session_id: int
    patient_id: int
    state: Optional[str] = None
    assessment_score: Optional[int] = None
    risk_level: Optional[str] = None
    selected_experts: Optional[str] = None
    user_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    messages: List[ConsultationMessageResponse] = []
    agent_results: List[ConsultationAgentResultResponse] = []
    report: Optional[ConsultationReportBrief] = None


class UserContentConfigPreviewItem(BaseModel):
    """预览用的配置项"""
    model_config = ConfigDict(extra='ignore')

    name: str
    type: str
    enabled: bool = True
    customText: Optional[str] = None
    indicatorCount: Optional[int] = None
    recentCount: Optional[int] = None
    category: Optional[str] = None
    contentLimit: Optional[int] = None
    findingsLimit: Optional[int] = None


class PromptPreviewRequest(BaseModel):
    """提示词预览请求"""
    patient_id: int
    system_prompt: str = "你是一名肿瘤科专家"
    time_range_days: int = 60
    user_content_config: List[UserContentConfigPreviewItem]
