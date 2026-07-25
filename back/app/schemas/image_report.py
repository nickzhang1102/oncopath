"""上传报告 Pydantic Schemas"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


class OCRStatus(str, Enum):
    """OCR状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    PENDING_REVIEW = "pending_review"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEWED = "reviewed"


class ImageCategoryBase(BaseModel):
    """图片分类基础模型"""
    category_key: str = Field(..., description="分类key")
    category_name: str = Field(..., description="分类名称")
    icon: Optional[str] = Field(None, description="图标")
    color: Optional[str] = Field(None, description="颜色")
    description: Optional[str] = Field(None, description="描述")
    sort_order: int = Field(0, description="排序")
    group_key: Optional[str] = Field(None, description="分组标识")
    report_type: Optional[str] = Field(None, description="OCR报告类型: lab/exam/pathology")


class ImageCategoryResponse(ImageCategoryBase):
    """图片分类响应模型"""
    model_config = ConfigDict(from_attributes=True)

    category_id: int
    is_active: bool = True


class ImageReportBase(BaseModel):
    """上传报告基础模型"""
    title: str = Field(..., max_length=200, description="报告标题")
    description: Optional[str] = Field(None, description="描述")
    category: str = Field(..., max_length=50, description="分类key")
    hospital: Optional[str] = Field(None, max_length=100, description="医院代码")
    department: Optional[str] = Field(None, max_length=100, description="科室代码")
    capture_date: Optional[date] = Field(None, description="检查日期")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    notes: Optional[str] = Field(None, description="备注")
    is_private: bool = Field(True, description="是否私有")
    is_important: bool = Field(False, description="是否重要")

    @field_validator('capture_date', mode='before')
    @classmethod
    def empty_date_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class ImageReportCreate(ImageReportBase):
    """创建上传报告请求模型"""
    patient_id: int = Field(..., description="患者ID")
    image_data: str = Field(..., description="Base64编码的图片数据")
    image_type: str = Field("jpeg", description="文件类型: jpeg, png, pdf")


class ImageReportUpdate(BaseModel):
    """更新上传报告请求模型"""
    title: Optional[str] = Field(None, max_length=200, description="报告标题")
    description: Optional[str] = Field(None, description="描述")
    category: Optional[str] = Field(None, max_length=50, description="分类key")
    hospital: Optional[str] = Field(None, max_length=100, description="医院代码")
    department: Optional[str] = Field(None, max_length=100, description="科室代码")
    capture_date: Optional[date] = Field(None, description="检查日期")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    notes: Optional[str] = Field(None, description="备注")
    is_private: Optional[bool] = Field(None, description="是否私有")

    @field_validator('capture_date', mode='before')
    @classmethod
    def empty_date_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v

    is_important: Optional[bool] = Field(None, description="是否重要")


class ImageReportResponse(ImageReportBase):
    """上传报告响应模型"""
    model_config = ConfigDict(from_attributes=True)

    report_id: int
    patient_id: int
    account_id: int
    image_type: Optional[str] = None
    image_size: Optional[int] = None
    page_count: Optional[int] = None
    ocr_text: Optional[str] = None
    ocr_status: Optional[str] = "pending"
    matched_count: Optional[int] = 0
    total_count: Optional[int] = 0
    upload_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    # 分类中文名称
    category_name: Optional[str] = Field(None, description="分类中文名称")
    
    # 报告类型和关联
    report_type: Optional[str] = Field(None, description="报告类型: lab/exam/pathology")
    related_check_id: Optional[int] = Field(None, description="关联的检验记录ID")
    related_exam_id: Optional[int] = Field(None, description="关联的检查记录ID")
    related_pathology_id: Optional[int] = Field(None, description="关联的病理记录ID")
    extracted_info: Optional[dict] = Field(None, description="LLM提取的结构化信息")

    # 缩略图
    thumbnail_url: Optional[str] = Field(None, description="缩略图访问URL")


class ImageReportDetail(ImageReportResponse):
    """上传报告详情响应模型（包含图片数据）"""
    image_data: Optional[str] = Field(None, description="Base64编码的图片数据")
    matching_details: Optional[dict] = Field(None, description="匹配详情")


class ImageReportListResponse(BaseModel):
    """上传报告列表响应"""
    items: List[ImageReportResponse]
    total: int
    pages: int
    current_page: int
    per_page: int
    hospitals: List[str] = []


class ImageReportStats(BaseModel):
    """上传报告统计"""
    total_count: int
    category_stats: List[dict] = []
    hospital_stats: List[dict] = []
    recent_reports: List[ImageReportResponse] = []


class MatchedIndicator(BaseModel):
    """匹配的指标"""
    raw_name: str = Field(..., description="原始名称")
    normalized_name: str = Field(..., description="标准化名称")
    value: Optional[str] = Field(None, description="指标值")
    unit: Optional[str] = Field(None, description="单位")
    reference: Optional[str] = Field(None, description="参考值")
    status: Optional[str] = Field(None, description="状态: normal/abnormal")

    # 匹配结果
    matched_index_id: Optional[int] = Field(None, description="匹配的标准指标ID")
    matched_name: Optional[str] = Field(None, description="匹配的标准名称")
    match_confidence: Optional[float] = Field(None, description="匹配置信度")
    match_method: Optional[str] = Field(None, description="匹配方法: exact/vector/llm")


class OCRResult(BaseModel):
    """OCR识别结果"""
    raw_text: str = Field(..., description="原始文本")
    indicators: List[MatchedIndicator] = []
    total_count: int = 0
    matched_count: int = 0