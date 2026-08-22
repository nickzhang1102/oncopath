"""会诊对话 Schema

包含：
- Conversation CRUD
- Leader Session 管理
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ===== Enum =====

class ConversationStatus(str, Enum):
    NEW = "new"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    ERROR = "error"


class LeaderState(str, Enum):
    IDLE = "idle"
    ASSESSING = "assessing"
    QUESTIONING = "questioning"
    FORMING_TEAM = "forming_team"
    WEB_SEARCH = "web_search"
    MONITORING = "monitoring"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ===== Conversation =====

class ConversationCreate(BaseModel):
    """创建会诊对话"""
    patient_id: int


class ConversationResponse(BaseModel):
    """会诊对话响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: Optional[str] = None
    user_id: int
    patient_id: Optional[int] = None
    is_archived: bool = False
    is_review_mode: bool = False
    share_token: Optional[str] = None
    has_share_password: bool = False
    share_expire_at: Optional[datetime] = None
    category: str = "medical"
    status: str = "new"
    provider: Optional[str] = None
    external_session_status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConversationListResponse(BaseModel):
    """会诊列表响应"""
    conversations: List[ConversationResponse]
    total: int
    limit: int
    offset: int


class ConversationDetailResponse(ConversationResponse):
    """会诊详情响应（含会话数据）"""
    leader_sessions: List["LeaderSessionResponse"] = []


# ===== Message =====

class MessageResponse(BaseModel):
    """消息响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    role: str
    content: Optional[str] = None
    raw_content: Optional[str] = None
    leader_session_id: Optional[int] = None
    message_type: str = "normal"
    is_review_mode: bool = False
    sequence_number: int = 0
    created_at: Optional[datetime] = None


# ===== Leader Session =====

class StartLeaderSessionRequest(BaseModel):
    """启动 Leader 会诊请求"""
    patient_id: int
    conversation_id: Optional[int] = Field(None, description="已存在的对话 ID，为空则新建")


class AnswerQuestionsRequest(BaseModel):
    """回答追问请求（body 传 session_id）"""
    session_id: int
    answers: List[str] = Field(..., min_length=1, description="回答列表")


class AnswerQuestionsBody(BaseModel):
    """回答追问请求（URL path 传 session_id）"""
    answers: List[str] = Field(..., min_length=1, description="回答列表")


class StopSessionRequest(BaseModel):
    """停止会诊请求"""
    session_id: int


class LeaderSessionResponse(BaseModel):
    """Leader 会话响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    patient_id: Optional[int] = None
    state: str = "idle"
    assessment_score: Optional[int] = None
    risk_level: str = "medium"
    selected_agents: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_tokens: int = 0
    total_cost: float = 0.0
    stop_requested: bool = False
    user_message: Optional[str] = None


class LeaderMessageResponse(BaseModel):
    """Leader 消息响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: Optional[int] = None
    leader_session_id: int
    message_type: str
    content: Optional[dict] = None
    sequence_number: int
    created_at: Optional[datetime] = None


class LeaderAgentResultResponse(BaseModel):
    """专家分析结果响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: Optional[int] = None
    leader_session_id: int
    agent_id: str
    agent_name: str
    status: str
    content: Optional[str] = None
    error: Optional[str] = None
    sequence_number: int
    created_at: Optional[datetime] = None


class LeaderFinalReportResponse(BaseModel):
    """综合报告响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: Optional[int] = None
    leader_session_id: int
    report: str
    created_at: Optional[datetime] = None


class SessionDataResponse(BaseModel):
    """会话完整数据响应（前端恢复用）"""
    conversation: ConversationResponse
    session: Optional[LeaderSessionResponse] = None
    messages: List[LeaderMessageResponse] = []
    agent_results: List[LeaderAgentResultResponse] = []
    final_report: Optional[LeaderFinalReportResponse] = None
    conversation_messages: List[MessageResponse] = []


class ShareSessionResponse(BaseModel):
    """分享会话响应"""
    conversation: ConversationResponse
    session: Optional[LeaderSessionResponse] = None
    messages: List[LeaderMessageResponse] = []
    agent_results: List[LeaderAgentResultResponse] = []
    final_report: Optional[LeaderFinalReportResponse] = None


class GenerateShareTokenRequest(BaseModel):
    """生成分享令牌请求"""
    password: Optional[str] = Field(None, min_length=4, max_length=32, description="分享密码（可选）")
    expire_hours: Optional[int] = Field(None, ge=1, le=720, description="有效期小时数（可选，不设则永不过期）")


class GenerateShareTokenResponse(BaseModel):
    """生成分享令牌响应"""
    share_token: str
    share_url: str
    has_password: bool = False
    expire_at: Optional[datetime] = None


class VerifySharePasswordRequest(BaseModel):
    """验证分享密码请求"""
    password: str = Field(..., min_length=1, max_length=32)


# ===== Admin 指标库管理 Schema =====

class AdminIndexCreate(BaseModel):
    index_code: Optional[str] = Field(None, max_length=50)
    index_name: str = Field(..., max_length=100)
    index_name_en: Optional[str] = Field(None, max_length=100)
    index_unit: Optional[str] = Field(None, max_length=20)
    category: Optional[str] = Field(None, max_length=50)
    sub_category: Optional[str] = Field(None, max_length=50)
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    reference_range: Optional[dict] = None
    description: Optional[str] = None
    is_chart: bool = True
    is_edit: bool = True
    sort: int = 0


class AdminIndexUpdate(BaseModel):
    index_code: Optional[str] = Field(None, max_length=50)
    index_name: Optional[str] = Field(None, max_length=100)
    index_name_en: Optional[str] = Field(None, max_length=100)
    index_unit: Optional[str] = Field(None, max_length=20)
    category: Optional[str] = Field(None, max_length=50)
    sub_category: Optional[str] = Field(None, max_length=50)
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    reference_range: Optional[dict] = None
    description: Optional[str] = None
    is_chart: Optional[bool] = None
    is_edit: Optional[bool] = None
    sort: Optional[int] = None


class AdminIndexStatusToggle(BaseModel):
    is_active: bool


class AdminIndexSortItem(BaseModel):
    index_id: int
    sort: int


class AdminIndexSortRequest(BaseModel):
    items: List[AdminIndexSortItem] = Field(..., min_length=1)


class AdminIndexImportItem(BaseModel):
    index_code: Optional[str] = None
    index_name: str = Field(..., max_length=100)
    index_name_en: Optional[str] = None
    index_unit: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    reference_range: Optional[dict] = None
    description: Optional[str] = None
    is_chart: bool = True
    is_edit: bool = True
    sort: int = 0


class AdminIndexImportRequest(BaseModel):
    indices: List[AdminIndexImportItem] = Field(..., min_length=1, max_length=500)


class AdminIndexItem(BaseModel):
    index_id: int
    index_code: Optional[str] = None
    index_name: str
    index_name_en: Optional[str] = None
    index_unit: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    reference_range: Optional[dict] = None
    description: Optional[str] = None
    is_chart: bool = True
    is_edit: bool = True
    sort: int = 0
    is_active: bool
    is_system: bool
    match_count: int
    model_config = ConfigDict(from_attributes=True)


class AdminIndexImportResult(BaseModel):
    created: int
    skipped: int
    errors: List[str]


class IndexCategoryCreate(BaseModel):
    category_key: str = Field(..., max_length=50, pattern=r'^[a-z][a-z0-9_]*$')
    category_name: str = Field(..., max_length=100)
    sort: int = 0
    icon: Optional[str] = Field(None, max_length=10)
    color: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = Field(None, max_length=200)
    group_key: Optional[str] = Field(None, max_length=50)
    report_type: Optional[str] = Field(None, max_length=20)


class IndexCategoryUpdate(BaseModel):
    category_name: Optional[str] = Field(None, max_length=100)
    sort: Optional[int] = None
    icon: Optional[str] = Field(None, max_length=10)
    color: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = Field(None, max_length=200)
    group_key: Optional[str] = Field(None, max_length=50)
    report_type: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class IndexCategoryItem(BaseModel):
    category_key: str
    category_name: str
    sort: int
    is_active: bool
    icon: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    group_key: Optional[str] = None
    report_type: Optional[str] = None
    index_count: int
    model_config = ConfigDict(from_attributes=True)
