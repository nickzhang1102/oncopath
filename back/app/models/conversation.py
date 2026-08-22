"""会诊对话数据模型

采用对话式流式会诊架构（ConversationDisplay），包含：
- Conversation: 会诊对话主表
- Message: 对话消息
- LeaderSession: Leader 状态机
- LeaderMessage: Leader 消息流
- LeaderAgentResult: 专家分析结果
- LeaderFinalReport: 综合报告
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean,
    UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.time_utils import get_utc_now


class Conversation(Base):
    """会诊对话主表"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=True, comment="对话标题（患者姓名 + 会诊摘要）")
    user_id = Column(Integer, ForeignKey("login_account.account_id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patient.patient_id"), nullable=True, index=True, comment="oncopath 扩展：关联患者")
    is_archived = Column(Boolean, default=False, nullable=False, comment="是否归档")
    is_review_mode = Column(Boolean, default=False, nullable=False, comment="评审模式")
    share_token = Column(String(20), unique=True, index=True, comment="分享令牌")
    share_password = Column(String(100), nullable=True, comment="分享密码(bcrypt哈希)")
    share_expire_at = Column(DateTime, nullable=True, comment="分享过期时间")
    category = Column(String(20), default="medical", index=True, comment="分类")
    status = Column(String(20), default="new", index=True, comment="new/analyzing/completed/error")
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    __table_args__ = (
        Index("ix_conversations_user_updated", "user_id", "updated_at"),
    )

    # 关系
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan",
                            order_by="Message.sequence_number")
    leader_sessions = relationship("LeaderSession", back_populates="conversation", cascade="all, delete-orphan")
    external_session = relationship("ConsultationExternalSession", back_populates="conversation", uselist=False,
                                    cascade="all, delete-orphan")
    user = relationship("LoginAccount", back_populates="conversations_v2")
    patient = relationship("Patient")


class ConsultationExternalSession(Base):
    """外部会诊会话映射"""
    __tablename__ = "consultation_external_sessions"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    provider = Column(String(50), default="agentteams", nullable=False, index=True)
    launch_request_id = Column(String(100), nullable=True)
    external_conversation_id = Column(String(100), nullable=False)
    external_session_id = Column(String(100), nullable=True)
    external_share_token = Column(String(200), nullable=True)
    embed_url = Column(Text, nullable=False)
    status = Column(String(20), default="created", nullable=False, index=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    conversation = relationship("Conversation", back_populates="external_session")

    __table_args__ = (
        Index("ix_consultation_external_provider_status", "provider", "status"),
        UniqueConstraint("provider", "launch_request_id", name="uq_consultation_external_provider_request"),
    )


class Message(Base):
    """对话消息"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False, comment="user/assistant")
    content = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=True)
    leader_session_id = Column(Integer, ForeignKey("leader_sessions.id"), nullable=True)
    message_type = Column(String(20), default="normal",
                          comment="normal/leader_thinking/leader_question/agent_result/leader_summary")
    is_review_mode = Column(Boolean, default=False)
    sequence_number = Column(Integer, default=0)
    created_at = Column(DateTime, default=get_utc_now)

    # 关系
    conversation = relationship("Conversation", back_populates="messages")


class LeaderSession(Base):
    """Leader 状态机"""
    __tablename__ = "leader_sessions"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patient.patient_id"), nullable=True, comment="oncopath 扩展")
    user_message = Column(Text, nullable=False, comment="自动收集的病历上下文")
    state = Column(String(20), default="idle",
                   comment="idle/assessing/questioning/forming_team/web_search/monitoring/summarizing/completed/stopped/failed")
    assessment_score = Column(Integer, nullable=True, comment="0-100")
    risk_level = Column(String(10), default="medium", comment="low/medium/high")
    selected_agents = Column(String(500), nullable=True, comment="逗号分隔的专家 ID")
    started_at = Column(DateTime, default=get_utc_now)
    completed_at = Column(DateTime, nullable=True)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    stop_requested = Column(Boolean, default=False)

    # 关系
    conversation = relationship("Conversation", back_populates="leader_sessions")
    leader_messages = relationship("LeaderMessage", back_populates="leader_session",
                                  cascade="all, delete-orphan", order_by="LeaderMessage.sequence_number")
    agent_results = relationship("LeaderAgentResult", back_populates="leader_session",
                                cascade="all, delete-orphan", order_by="LeaderAgentResult.sequence_number")
    final_report = relationship("LeaderFinalReport", back_populates="leader_session",
                               uselist=False, cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index("ix_leader_sessions_conversation_state", "conversation_id", "state"),
        Index("ix_leader_sessions_patient_id", "patient_id"),
    )


class LeaderMessage(Base):
    """Leader 消息流"""
    __tablename__ = "leader_messages"

    id = Column(Integer, primary_key=True, index=True)
    leader_session_id = Column(Integer, ForeignKey("leader_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    message_type = Column(String(20), nullable=False,
                          comment="assessment/question/answer/team_config/progress/error/leader_thinking/leader_summarizing/execution_status/execution_stopped/web_search_result")
    content = Column(JSONB, nullable=True)
    sequence_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=get_utc_now)

    # 关系
    leader_session = relationship("LeaderSession", back_populates="leader_messages")

    # 约束
    __table_args__ = (
        UniqueConstraint("leader_session_id", "sequence_number", name="uq_leader_message_seq"),
    )


class LeaderAgentResult(Base):
    """专家分析结果"""
    __tablename__ = "leader_agent_results"

    id = Column(Integer, primary_key=True, index=True)
    leader_session_id = Column(Integer, ForeignKey("leader_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(50), nullable=False, comment="专家标识")
    agent_name = Column(String(100), nullable=False, comment="专家名称")
    status = Column(String(20), nullable=False, comment="success/failed")
    content = Column(Text, nullable=True, comment="分析内容")
    error = Column(Text, nullable=True, comment="错误信息")
    sequence_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=get_utc_now)

    # 关系
    leader_session = relationship("LeaderSession", back_populates="agent_results")

    # 约束
    __table_args__ = (
        UniqueConstraint("leader_session_id", "sequence_number", name="uq_agent_result_seq"),
    )


class LeaderFinalReport(Base):
    """综合报告"""
    __tablename__ = "leader_final_reports"

    id = Column(Integer, primary_key=True, index=True)
    leader_session_id = Column(Integer, ForeignKey("leader_sessions.id", ondelete="CASCADE"),
                               unique=True, nullable=False)
    report = Column(Text, nullable=False, comment="Markdown 格式")
    created_at = Column(DateTime, default=get_utc_now)

    # 关系
    leader_session = relationship("LeaderSession", back_populates="final_report")

