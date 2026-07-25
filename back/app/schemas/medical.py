from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import date, datetime


def _empty_date_to_none(cls, v):
    """将空字符串转为 None，避免 Pydantic 尝试解析空字符串为日期"""
    if v == '' or v is None:
        return None
    return v

# MedicalIndex
class MedicalIndexResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    index_id: int
    index_name: str
    index_unit: Optional[str]
    reference_min: Optional[float]
    reference_max: Optional[float]
    category: Optional[str] = None
    is_chart: bool
    description: Optional[str]
    sort: int
    is_edit: bool

class MedicalIndexQuery(BaseModel):
    category: Optional[str] = None
    limit: Optional[int] = 100

# MedicalCheck
class MedicalCheckDetailCreate(BaseModel):
    index_name: str = Field(max_length=100)
    index_value: Optional[str] = Field(default=None, max_length=100)
    index_unit: Optional[str] = Field(default=None, max_length=50)
    reference_value: Optional[str] = Field(default=None, max_length=200)
    index_status: Optional[str] = Field(default=None, max_length=50)

class MedicalCheckCreate(BaseModel):
    patient_id: int
    medical_date: date
    hospital: Optional[str] = Field(default=None, max_length=100)
    comment: Optional[str] = Field(default=None, max_length=5000)
    details: List[MedicalCheckDetailCreate]

class MedicalCheckDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    medical_detail_id: int
    medical_id: int
    index_id: Optional[int] = None
    index_name: str
    index_value: Optional[str]
    index_unit: Optional[str]
    reference_value: Optional[str]
    index_status: Optional[str]
    category: Optional[str] = None

class MedicalCheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    medical_id: int
    patient_id: int
    medical_date: date
    hospital: Optional[str]
    comment: Optional[str]
    status: str
    category: Optional[str] = None
    category_name: Optional[str] = None
    category_icon: Optional[str] = None
    category_color: Optional[str] = None
    created_at: Optional[datetime] = None
    details: List[MedicalCheckDetailResponse] = []

    # AI 解读
    interpretation: Optional[str] = None
    interpretation_at: Optional[datetime] = None

class MedicalCheckQuery(BaseModel):
    patient_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    category: Optional[str] = None
    limit: int = 100
    offset: int = 0

    _normalize_start = field_validator('start_date', mode='before')(classmethod(_empty_date_to_none))
    _normalize_end = field_validator('end_date', mode='before')(classmethod(_empty_date_to_none))

# MedicalExam
class MedicalExamCreate(BaseModel):
    patient_id: int
    medical_date: Optional[date] = None
    hospital: Optional[str] = Field(default=None, max_length=100)
    title: Optional[str] = Field(default=None, max_length=200)
    exam_type: Optional[str] = Field(default=None, max_length=50)
    exam_info: Optional[str] = Field(default=None, max_length=10000)
    exam_diag: Optional[str] = Field(default=None, max_length=10000)
    comment: Optional[str] = Field(default=None, max_length=5000)

    _normalize_date = field_validator('medical_date', mode='before')(classmethod(_empty_date_to_none))

class MedicalExamUpdate(BaseModel):
    """更新检查报告（仅提交的字段会被更新）"""
    medical_date: Optional[date] = None
    hospital: Optional[str] = Field(default=None, max_length=100)
    title: Optional[str] = Field(default=None, max_length=200)
    exam_type: Optional[str] = Field(default=None, max_length=50)
    exam_info: Optional[str] = Field(default=None, max_length=10000)
    exam_diag: Optional[str] = Field(default=None, max_length=10000)
    comment: Optional[str] = Field(default=None, max_length=5000)

    _normalize_date = field_validator('medical_date', mode='before')(classmethod(_empty_date_to_none))

class MedicalExamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exam_id: int
    patient_id: int
    medical_date: Optional[date]
    hospital: Optional[str]
    title: Optional[str]
    exam_type: Optional[str]
    exam_info: Optional[str]
    exam_diag: Optional[str]
    comment: Optional[str]
    created_at: Optional[datetime] = None
    image_report_id: Optional[int] = None

    # AI 解读
    interpretation: Optional[str] = None
    interpretation_at: Optional[datetime] = None

class MedicalExamQuery(BaseModel):
    patient_id: int
    exam_type: Optional[str] = None
    limit: int = 100
    offset: int = 0

# PathologyReport
class IHCMarkerCreate(BaseModel):
    marker_name: str = Field(max_length=100, description="标记物名称")
    result: Optional[str] = Field(default=None, max_length=50, description="结果")
    intensity: Optional[str] = Field(default=None, max_length=20, description="染色强度")
    percentage: Optional[str] = Field(default=None, max_length=20, description="阳性细胞百分比")

class IHCMarkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    report_id: int
    marker_name: str
    result: Optional[str]
    intensity: Optional[str]
    percentage: Optional[str]

class PathologyReportQuery(BaseModel):
    patient_id: int
    offset: int = Field(default=0, ge=0, description="偏移量")
    limit: int = Field(default=100, ge=1, le=1000, description="返回数量限制")

class PathologyReportCreate(BaseModel):
    patient_id: int
    report_title: Optional[str] = Field(default=None, max_length=200)
    report_date: Optional[date] = None
    hospital: Optional[str] = Field(default=None, max_length=100)
    comment: Optional[str] = Field(default=None, max_length=5000)
    image_data: Optional[str] = None  # base64
    image_type: Optional[str] = Field(default=None, max_length=20, description="文件类型: jpeg, png, pdf")
    diagnosis: Optional[str] = Field(default=None, max_length=5000, description="病理诊断")
    cancer_type: Optional[str] = Field(default=None, max_length=100, description="癌种/肿瘤类型")
    stage: Optional[str] = Field(default=None, max_length=50, description="临床分期")
    histology_type: Optional[str] = Field(default=None, max_length=100, description="组织学类型")
    immunohistochemistry: Optional[str] = Field(default=None, max_length=5000, description="免疫组化结果(文本,兼容旧格式)")
    gene_testing: Optional[str] = Field(default=None, max_length=5000, description="基因检测信息")
    ihc_markers: Optional[List[IHCMarkerCreate]] = Field(default=None, description="免疫组化标记物列表(结构化)")

    _normalize_date = field_validator('report_date', mode='before')(classmethod(_empty_date_to_none))

class PathologyReportUpdate(BaseModel):
    """更新病理报告（仅提交的字段会被更新）"""
    report_title: Optional[str] = Field(default=None, max_length=200)
    report_date: Optional[date] = None
    hospital: Optional[str] = Field(default=None, max_length=100)
    comment: Optional[str] = Field(default=None, max_length=5000)
    image_data: Optional[str] = None  # base64，传 null 清除图片
    diagnosis: Optional[str] = Field(default=None, max_length=5000, description="病理诊断")
    cancer_type: Optional[str] = Field(default=None, max_length=100, description="癌种/肿瘤类型")
    stage: Optional[str] = Field(default=None, max_length=50, description="临床分期")
    histology_type: Optional[str] = Field(default=None, max_length=100, description="组织学类型")
    immunohistochemistry: Optional[str] = Field(default=None, max_length=5000, description="免疫组化结果(文本,兼容旧格式)")
    gene_testing: Optional[str] = Field(default=None, max_length=5000, description="基因检测信息")
    ihc_markers: Optional[List[IHCMarkerCreate]] = Field(default=None, description="免疫组化标记物列表(结构化,传则全覆盖)")

    _normalize_date = field_validator('report_date', mode='before')(classmethod(_empty_date_to_none))

class PathologyReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: int
    patient_id: int
    report_title: Optional[str]
    report_date: Optional[date]
    hospital: Optional[str]
    comment: Optional[str]
    has_image: bool
    diagnosis: Optional[str] = None
    cancer_type: Optional[str] = None
    stage: Optional[str] = None
    histology_type: Optional[str] = None
    immunohistochemistry: Optional[str] = None
    gene_testing: Optional[str] = None
    ihc_markers: List[IHCMarkerResponse] = []
    created_at: Optional[datetime] = None

    # AI 解读
    interpretation: Optional[str] = None
    interpretation_at: Optional[datetime] = None

# MedicalRecord
class MedicalRecordQuery(BaseModel):
    patient_id: int
    limit: int = Field(default=100, ge=1, le=1000, description="返回数量限制")

class MedicalRecordCreate(BaseModel):
    patient_id: int
    record_name: Optional[str] = Field(default=None, max_length=100)
    record_date: Optional[date] = None
    record_info: Optional[str] = Field(default=None, max_length=10000)
    record_type: Optional[str] = Field(default=None, max_length=50)
    patient_status: Optional[str] = Field(default=None, max_length=50)
    comment: Optional[str] = Field(default=None, max_length=5000)
    record_drug: Optional[str] = Field(default=None, max_length=500)
    hospital: Optional[str] = Field(default=None, max_length=200)

    _normalize_date = field_validator('record_date', mode='before')(classmethod(_empty_date_to_none))

class MedicalRecordUpdate(BaseModel):
    """更新病情记录（仅提交的字段会被更新）"""
    record_name: Optional[str] = Field(default=None, max_length=100)
    record_info: Optional[str] = Field(default=None, max_length=10000)
    record_type: Optional[str] = Field(default=None, max_length=50)
    record_date: Optional[date] = None
    patient_status: Optional[str] = Field(default=None, max_length=50)
    comment: Optional[str] = Field(default=None, max_length=5000)
    hospital: Optional[str] = Field(default=None, max_length=200)

    _normalize_date = field_validator('record_date', mode='before')(classmethod(_empty_date_to_none))

class MedicalRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    record_id: int
    patient_id: int
    record_name: Optional[str]
    record_date: Optional[date]
    record_info: Optional[str]
    record_type: Optional[str]
    patient_status: Optional[str]
    comment: Optional[str]
    record_drug: Optional[str]
    hospital: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

# IndexValue Query
class IndexValueQuery(BaseModel):
    patient_id: int
    index_name: Optional[str] = None
    category: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    limit: int = Field(default=100, ge=1, le=1000, description="返回数量限制，最大1000")

    _normalize_start = field_validator('start_date', mode='before')(classmethod(_empty_date_to_none))
    _normalize_end = field_validator('end_date', mode='before')(classmethod(_empty_date_to_none))

# ===== 原版UI支持响应模型 =====
class StandardIndexInfo(BaseModel):
    """标准指标信息"""
    index_id: int
    index_name: str
    index_unit: Optional[str]
    reference_min: Optional[float]
    reference_max: Optional[float]

class IndexDetailForCheck(BaseModel):
    """检验明细信息"""
    detail_id: int
    index_name: str
    index_value: Optional[str]
    index_unit: Optional[str]
    reference_value: Optional[str]
    index_status: Optional[str]
    standard_index: Optional[StandardIndexInfo] = None

class LatestCheckDataResponse(BaseModel):
    """最新检验数据响应"""
    medical_id: int
    medical_date: Optional[str]
    hospital: Optional[str]
    comment: Optional[str]
    indices: List[IndexDetailForCheck] = []

class IndexListResponse(BaseModel):
    """指标列表响应"""
    index_id: int
    index_code: Optional[str]
    index_name: str
    index_unit: Optional[str]
    reference_min: Optional[float]
    reference_max: Optional[float]
    category: Optional[str]
    sub_category: Optional[str]
    description: Optional[str]
    is_chart: bool

class IndexHistoryItem(BaseModel):
    """指标历史项"""
    index_name: str
    index_value: Optional[str]
    index_unit: Optional[str]
    reference_value: Optional[str]
    index_status: Optional[str]
    medical_date: Optional[str]
    hospital: Optional[str]
    medical_id: int

class LatestExamResponse(BaseModel):
    """最新检查报告响应"""
    exam_id: int
    medical_date: Optional[str]
    hospital: Optional[str]
    exam_type: Optional[str]
    exam_info: Optional[str]
    exam_diag: Optional[str]
    comment: Optional[str]


# ===== 指标分类和收藏相关 =====
class IndexCategoryResponse(BaseModel):
    """指标分类响应"""
    category_key: str
    category_name: str
    icon: Optional[str] = None
    color: Optional[str] = None


class ManualCheckDetailCreate(BaseModel):
    """手动添加检验明细请求"""
    patient_id: Optional[int] = None
    medical_date: str
    hospital: Optional[str] = None
    index_id: Optional[int] = None
    index_name: str
    index_value: str
    index_unit: Optional[str] = None
    reference_value: Optional[str] = None
    index_status: Optional[str] = None


class MedicalCheckCommentUpdate(BaseModel):
    """更新检验报告备注"""
    comment: Optional[str] = None


class IndexWithFavoriteResponse(BaseModel):
    """带收藏标记的指标响应"""
    index_id: int
    index_code: Optional[str]
    index_name: str
    index_unit: Optional[str]
    reference_min: Optional[float]
    reference_max: Optional[float]
    category: Optional[str]
    description: Optional[str]
    is_chart: bool
    is_edit: bool
    is_favorited: bool = False


# ===== 指标对比 =====

class IndexCompareRequest(BaseModel):
    """指标对比请求"""
    index_ids: List[int] = Field(..., min_length=2, description="要对比的指标ID列表，至少2个")
    patient_id: Optional[int] = Field(None, description="患者ID（可选）")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")


class IndexCompareItem(BaseModel):
    """对比结果中单个指标的元信息"""
    index_id: int
    index_name: str
    index_unit: Optional[str] = None
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    is_chart: bool = True


class IndexCompareResponse(BaseModel):
    """指标对比响应"""
    indexes: List[IndexCompareItem]
    aligned_data: List[dict]  # [{ date: "2026-05-28", values: { 3: "6.5", 7: "135" } }, ...]


# ===== 指标组合 =====

class IndexGroupCreate(BaseModel):
    """创建指标组合请求"""
    patient_id: int = Field(..., description="关联患者ID")
    group_name: str = Field(..., max_length=50, description="组合名称")
    index_ids: List[int] = Field(..., min_length=2, description="指标ID列表，至少2个")


class IndexGroupResponse(BaseModel):
    """指标组合响应"""
    id: int
    patient_id: int
    group_name: str
    index_ids: List[int]
    created_at: Optional[datetime] = None