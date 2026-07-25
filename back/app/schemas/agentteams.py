"""AgentTeams 集成配置 Schema"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


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
