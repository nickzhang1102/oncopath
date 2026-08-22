"""LLM 配置管理 Schema"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class LLMConfigItem(BaseModel):
    """LLM 配置项响应"""
    id: int
    config_key: str
    config_value: str
    config_group: str
    display_name: str
    description: Optional[str] = None
    is_secret: bool
    is_active: bool
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LLMConfigUpdateItem(BaseModel):
    """组更新中的单个配置项"""
    config_key: str
    config_value: str


class LLMConfigGroupUpdate(BaseModel):
    """按分组批量更新请求（单事务落库，保存后整组应用）"""
    updates: List[LLMConfigUpdateItem] = Field(..., min_length=1)


class LLMConfigTestRequest(BaseModel):
    """LLM 配置测试请求"""
    group: str = Field(..., pattern=r'^(consultation|interpretation|ocr)$', description="配置组")


class LLMConfigTestResponse(BaseModel):
    """LLM 配置测试响应"""
    success: bool
    message: str
    latency_ms: Optional[int] = None


class LLMConfigStatusResponse(BaseModel):
    """LLM 配置状态响应（首启弹窗判定用）"""
    configured: bool
