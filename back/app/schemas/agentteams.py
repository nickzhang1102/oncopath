"""AgentTeams 集成配置 Schema"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator
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
    upsell: AgentTeamsUpsell = Field(default_factory=AgentTeamsUpsell)


class AgentTeamsAvailabilityResponse(BaseModel):
    configured: bool
    enabled: bool
    base_url: str
    capacity: None = None
    upsell: AgentTeamsUpsell


class AgentTeamsStartRequest(BaseModel):
    patient_id: int
    conversation_id: Optional[int] = None
    request_id: Optional[UUID] = None

    @model_validator(mode="after")
    def require_request_id_for_new_launch(self):
        if self.conversation_id is None and self.request_id is None:
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


class AgentTeamsStartResponse(AgentTeamsExternalSessionResponse):
    pass


AgentTeamsSessionStatus = Literal[
    "created", "idle", "assessing", "questioning", "forming_team",
    "running", "web_search", "monitoring", "executing", "summarizing",
    "completed", "failed", "stopped",
]


class AgentTeamsStatusUpdate(BaseModel):
    status: AgentTeamsSessionStatus
