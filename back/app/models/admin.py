"""Admin 管理相关模型"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from app.core.database import Base
from app.utils.time_utils import get_utc_now


class LLMConfig(Base):
    """LLM 配置模型

    存储三组 LLM 配置（会诊/解读/OCR），
    支持数据库配置优先于环境变量，管理员可通过后台热更新。
    """
    __tablename__ = 'llm_configs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False, comment="配置键，如 consultation_api_key")
    config_value = Column(Text, nullable=False, comment="配置值，API Key 等敏感字段加密存储")
    config_group = Column(String(50), nullable=False, comment="配置组: consultation/interpretation/ocr")
    display_name = Column(String(100), nullable=False, comment="中文显示名")
    description = Column(Text, nullable=True, comment="配置说明")
    is_secret = Column(Boolean, default=False, comment="是否敏感字段，API 返回时掩码处理")
    is_active = Column(Boolean, default=False, comment="是否生效: true=数据库值优先, false=使用环境变量")
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    def __repr__(self):
        return f'<LLMConfig {self.config_key}>'


class AgentTeamsIntegrationConfig(Base):
    """AgentTeams 集成配置模型

    存储 OncoPath 调用 AgentTeams 所需的部署地址、启用状态、集成密钥
    以及未配置状态下的展示文案。集成密钥加密存储。
    """
    __tablename__ = 'agentteams_integration_configs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    base_url = Column(String(500), nullable=False, comment="AgentTeams 部署地址或同站反代路径")
    integration_secret = Column(Text, nullable=False, comment="加密存储的 AgentTeams 集成密钥")
    enabled = Column(Boolean, default=False, nullable=False, comment="是否启用 AgentTeams 集成")
    upsell_title = Column(String(100), nullable=True, comment="未配置提示标题")
    upsell_message = Column(Text, nullable=True, comment="未配置提示说明")
    demo_asset_url = Column(String(500), nullable=True, comment="演示资源 URL")
    cta_label = Column(String(100), nullable=True, comment="行动按钮文案")
    cta_url = Column(String(500), nullable=True, comment="行动按钮 URL")
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    def __repr__(self):
        return f'<AgentTeamsIntegrationConfig {self.base_url}>'
