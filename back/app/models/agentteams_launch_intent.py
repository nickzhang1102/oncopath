"""Durable OncoPath launch intents for AgentTeams reconciliation."""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.time_utils import get_utc_now


class AgentTeamsLaunchIntent(Base):
    """Local authority for one externally billed consultation launch."""

    UNRESOLVED_STATUSES = ("prepared", "dispatching", "confirming", "manual_review")

    __tablename__ = "agentteams_launch_intents"

    id = Column(Integer, primary_key=True)
    provider = Column(String(50), nullable=False, default="agentteams")
    request_id = Column(String(100), nullable=False)
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    account_id = Column(
        Integer,
        ForeignKey("login_account.account_id"),
        nullable=False,
        index=True,
    )
    patient_id = Column(
        Integer,
        ForeignKey("patient.patient_id"),
        nullable=False,
        index=True,
    )
    status = Column(String(20), nullable=False, default="prepared", index=True)
    payload_ciphertext = Column(Text, nullable=True)
    payload_hash = Column(String(64), nullable=False)
    payload_purged_at = Column(DateTime, nullable=True)
    external_conversation_id = Column(String(100), nullable=True)
    external_session_id = Column(String(100), nullable=True)
    external_share_token = Column(String(200), nullable=True)
    embed_url = Column(Text, nullable=True)
    remote_status = Column(String(20), nullable=True)
    # HTTP status returned by the provider for a terminal rejection.  Keeping
    # this separate from ``last_error_code`` lets the API preserve the stable
    # client-facing error contract without ever replaying the launch.
    last_error_status = Column(Integer, nullable=True)
    last_error_code = Column(String(100), nullable=True)
    last_error_message = Column(Text, nullable=True)
    dispatch_started_at = Column(DateTime, nullable=True)
    lease_owner = Column(String(64), nullable=True, index=True)
    lease_expires_at = Column(DateTime, nullable=True, index=True)
    next_attempt_at = Column(DateTime, nullable=True, index=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    conversation = relationship("Conversation")

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "request_id",
            name="uq_agentteams_launch_intent_provider_request",
        ),
        Index(
            "ix_agentteams_launch_intent_patient_status",
            "account_id",
            "patient_id",
            "status",
        ),
    )


class AgentTeamsLaunchIntentAudit(Base):
    """Append-only operator audit for manual launch reconciliation."""

    __tablename__ = "agentteams_launch_intent_audits"

    id = Column(Integer, primary_key=True)
    intent_id = Column(
        Integer,
        ForeignKey("agentteams_launch_intents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    request_id = Column(String(100), nullable=False, index=True)
    actor_account_id = Column(
        Integer,
        ForeignKey("login_account.account_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action = Column(String(50), nullable=False)
    before_status = Column(String(20), nullable=False)
    after_status = Column(String(20), nullable=False)
    reason = Column(Text, nullable=True)
    error_code = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
