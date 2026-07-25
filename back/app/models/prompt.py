"""提示词配置模型

存储用户的AI诊断提示词配置
"""

from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import json

from app.core.database import Base
from app.utils.time_utils import get_utc_now


class PromptConfig(Base):
    """提示词配置模型
    
    存储每个患者的提示词配置，包括系统提示词和用户内容配置
    """
    __tablename__ = 'prompt_config'

    config_id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('login_account.account_id'), nullable=False)
    patient_id = Column(Integer, ForeignKey('patient.patient_id'), nullable=False)
    system_prompt = Column(Text, nullable=False, default='你是一名肿瘤科专家')
    user_content_config = Column(Text, nullable=False, default='[]')  # JSON格式存储用户内容配置
    time_range_days = Column(Integer, default=60)  # 数据时间范围（天）
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # 关系
    account = relationship("LoginAccount", back_populates="prompt_configs")
    patient = relationship("Patient", back_populates="prompt_configs")

    def to_dict(self) -> dict:
        """转换为字典格式
        
        Returns:
            包含所有配置信息的字典
        """
        return {
            'config_id': self.config_id,
            'account_id': self.account_id,
            'patient_id': self.patient_id,
            'system_prompt': self.system_prompt,
            'user_content_config': json.loads(self.user_content_config) if self.user_content_config else [],
            'time_range_days': self.time_range_days,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<PromptConfig {self.config_id} - Patient {self.patient_id}>'