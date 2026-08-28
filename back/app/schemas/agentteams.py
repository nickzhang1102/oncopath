"""AgentTeams 集成配置 Schema"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from uuid import UUID


class AgentTeamsUpsell(BaseModel):
    title: str = ""
    message: str = ""
    demo_asset_url: str = ""
    cta_label: str = ""
    cta_url: str = ""


class AgentTeamsConfigResponse(BaseModel):
    configured: bool
    enabled: bool
    base_url: str
    integration_secret: str = ""
    has_integration_secret: bool
    upsell: AgentTeamsUpsell
    updated_at: Optional[datetime] = None


class AgentTeamsConfigUpdate(BaseModel):
    enabled: bool = False
    base_url: str = Field(default="")
    integration_secret: str = Field(default="")
    # Upsell copy remains accepted for API compatibility, but it is an
    # optional advanced field. The normal connection form only submits
    # enabled/base_url/integration_secret and must not rewrite copy stored by
    # an older deployment.
    upsell: AgentTeamsUpsell | None = None


class AgentTeamsAvailabilityResponse(BaseModel):
    configured: bool
    enabled: bool
    base_url: str
    # 运行时能力宣告（来自 agentTeams capabilities 端点；未配置或探测失败时为空）
    reachable: bool = False
    protocol_version: Optional[int] = None
    limits: Optional[dict] = None
    client_key: str = "agentteams"
    upsell: AgentTeamsUpsell


class AgentTeamsStartRequest(BaseModel):
    patient_id: int
    # Deprecated: 恢复历史会诊请使用 embed 刷新接口，conversation_id 启动旁路
    # 已被移除（绕过持久化状态机，网络超时时缺少可靠恢复记录）。
    conversation_id: Optional[int] = None
    request_id: Optional[UUID] = None

    @model_validator(mode="after")
    def require_request_id_for_new_launch(self):
        if self.conversation_id is not None:
            raise ValueError(
                "conversation_id is not supported; restart a launch with request_id"
            )
        if self.request_id is None:
            raise ValueError("request_id is required when starting a new consultation")
        return self


class AgentTeamsExternalSessionResponse(BaseModel):
    conversation_id: int
    provider: str = "agentteams"
    external_conversation_id: str
    external_session_id: Optional[str] = None
    external_share_token: Optional[str] = None
    embed_url: str
    status: str = "created"


class AgentTeamsLaunchIntentResponse(BaseModel):
    request_id: Optional[UUID] = None
    conversation_id: int
    patient_id: int
    launch_status: Literal[
        "prepared", "dispatching", "confirming", "accepted", "rejected", "manual_review"
    ]
    retry_after_seconds: int = 2
    provider: str = "agentteams"
    external_conversation_id: Optional[str] = None
    external_session_id: Optional[str] = None
    external_share_token: Optional[str] = None
    embed_url: Optional[str] = None
    status: str = "created"
    error: Optional[str] = None


AgentTeamsSessionStatus = Literal[
    "created", "idle", "assessing", "questioning", "forming_team",
    "running", "web_search", "monitoring", "executing", "summarizing",
    "completed", "failed", "stopped",
]


class AgentTeamsStatusUpdate(BaseModel):
    status: AgentTeamsSessionStatus


class AgentTeamsManualReviewResolveRequest(BaseModel):
    decision: Literal["confirmed_not_created"]
    reason: str = Field(min_length=10, max_length=1000)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 10:
            raise ValueError("reason must contain at least 10 non-whitespace characters")
        return normalized


class AgentTeamsLaunchIntentAdminItem(BaseModel):
    id: int
    request_id: str
    conversation_id: int
    account_id: int
    patient_id: int
    launch_status: str
    attempt_count: int
    remote_status: Optional[str] = None
    external_conversation_id: Optional[str] = None
    external_session_id: Optional[str] = None
    last_error_status: Optional[int] = None
    last_error_code: Optional[str] = None
    last_error_message: Optional[str] = None
    payload_hash: str
    payload_retained: bool
    payload_purged_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AgentTeamsLaunchIntentAuditItem(BaseModel):
    id: int
    actor_account_id: Optional[int] = None
    action: str
    before_status: str
    after_status: str
    reason: Optional[str] = None
    error_code: Optional[str] = None
    created_at: datetime


class AgentTeamsLaunchIntentAdminDetail(AgentTeamsLaunchIntentAdminItem):
    audits: list[AgentTeamsLaunchIntentAuditItem] = Field(default_factory=list)
