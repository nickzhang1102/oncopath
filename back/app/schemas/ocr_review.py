"""OCR审查日志 Pydantic Schemas"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class FieldCorrection(BaseModel):
    """单个字段修正"""
    field_name: str = Field(..., max_length=100, description="被修正的字段名")
    original_value: Optional[str] = Field(None, description="OCR原始值")
    corrected_value: Optional[str] = Field(None, description="用户修正值")


class OCRReviewCreate(BaseModel):
    """创建OCR审查日志请求"""
    report_id: int = Field(..., description="报告ID")
    report_type: str = Field(..., max_length=20, description="报告类型: lab/exam/pathology")
    corrections: List[FieldCorrection] = Field(..., description="修正列表")


class OCRReviewResponse(BaseModel):
    """OCR审查日志响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: int
    report_type: str
    field_name: str
    original_value: Optional[str] = None
    corrected_value: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class OCRReviewListResponse(BaseModel):
    """OCR审查日志列表响应"""
    items: List[OCRReviewResponse]
    total: int