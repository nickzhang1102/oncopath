"""上传报告模型

用于存储上传的上传报告及其OCR识别结果
"""
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base
from app.utils.time_utils import get_utc_now


class ImageReport(Base):
    """上传报告表"""
    __tablename__ = "image_report"

    report_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient.patient_id"), nullable=False)
    account_id = Column(Integer, ForeignKey("login_account.account_id"), nullable=False)

    # 基本信息
    title = Column(String(200), nullable=False, comment="报告标题")
    description = Column(Text, nullable=True, comment="描述")
    category = Column(String(50), nullable=False, comment="分类key")
    hospital = Column(String(100), nullable=True, comment="医院代码")
    department = Column(String(100), nullable=True, comment="科室代码")

    # 图片数据 - 已迁移至文件系统，数据库仅存路径
    image_type = Column(String(20), nullable=True, comment="文件类型: jpeg, png, pdf")
    image_size = Column(Integer, nullable=True, comment="文件大小(字节)")
    content_hash = Column(String(64), nullable=True, comment="文件内容SHA-256哈希(去重键)")
    image_path = Column(String(500), nullable=True, comment="文件存储路径(迁移后使用)")
    thumbnail_path = Column(String(500), nullable=True, comment="缩略图存储路径")
    page_count = Column(Integer, nullable=True, comment="PDF页数，图片时为null")

    # OCR识别结果
    ocr_text = Column(Text, nullable=True, comment="OCR识别的原始文本")
    ocr_status = Column(String(20), default="pending", comment="OCR状态: pending, processing, completed, failed")
    ocr_error = Column(Text, nullable=True, comment="OCR错误信息")

    # 指标匹配结果
    matched_count = Column(Integer, default=0, comment="匹配成功的指标数")
    total_count = Column(Integer, default=0, comment="识别的指标总数")
    matching_details = Column(JSONB, nullable=True, comment="匹配详情JSON")
    
    # LLM调试信息
    llm_raw_response = Column(Text, nullable=True, comment="LLM原始响应（用于调试）")
    
    # 报告类型和处理结果关联
    report_type = Column(String(20), nullable=True, comment="报告类型: lab/exam/pathology")
    related_check_id = Column(Integer, nullable=True, comment="关联的检验记录ID(medical_check)")
    related_exam_id = Column(Integer, nullable=True, comment="关联的检查记录ID(medical_exam)")
    related_pathology_id = Column(Integer, nullable=True, comment="关联的病理记录ID(pathology_report)")
    
    # LLM提取的结构化信息
    extracted_info = Column(JSONB, nullable=True, comment="LLM提取的结构化信息(JSON)")

    # 检查日期
    capture_date = Column(Date, nullable=True, comment="检查日期")

    # 标签和备注
    tags = Column(String(500), nullable=True, comment="标签，逗号分隔")
    notes = Column(Text, nullable=True, comment="备注")

    # 隐私和重要标记
    is_private = Column(Boolean, default=True, comment="是否私有")
    is_important = Column(Boolean, default=False, comment="是否重要")

    # 时间戳
    upload_date = Column(DateTime, default=get_utc_now, comment="上传时间")
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # 关系
    patient = relationship("Patient", back_populates="image_reports")
    account = relationship("LoginAccount", back_populates="image_reports")
    review_logs = relationship("OCRReviewLog", back_populates="image_report", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_image_report_patient_category', 'patient_id', 'category'),
        Index('idx_image_report_patient_ocr', 'patient_id', 'ocr_status'),
        Index('idx_image_report_dedup', 'patient_id', 'account_id', 'category', 'content_hash'),
    )

    # to_dict 默认排除的内部字段
    _SENSITIVE_FIELDS = frozenset({
        "llm_raw_response", "content_hash",
        "image_path", "thumbnail_path", "ocr_error",
    })

    def to_dict(self, include_image: bool = False, safe: bool = True):
        """转换为字典

        Args:
            include_image: 是否包含图片URL
            safe: 为True时排除敏感/内部字段（默认True）
        """
        result = {
            "report_id": self.report_id,
            "patient_id": self.patient_id,
            "account_id": self.account_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "hospital": self.hospital,
            "department": self.department,
            "image_type": self.image_type,
            "image_size": self.image_size,
            "page_count": self.page_count,
            "ocr_text": self.ocr_text,
            "ocr_status": self.ocr_status,
            "matched_count": self.matched_count,
            "total_count": self.total_count,
            "capture_date": self.capture_date.isoformat() if self.capture_date else None,
            "tags": self.tags.split(',') if self.tags else [],
            "notes": self.notes,
            "is_private": self.is_private,
            "is_important": self.is_important,
            "upload_date": self.upload_date.isoformat() if self.upload_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            # 新增字段
            "report_type": self.report_type,
            "related_check_id": self.related_check_id,
            "related_exam_id": self.related_exam_id,
            "related_pathology_id": self.related_pathology_id,
            "extracted_info": self.extracted_info,
        }

        # 缩略图URL - 指向API端点
        result["thumbnail_url"] = f"/image_reports/{self.report_id}/thumbnail"

        if include_image and self.image_path:
            # 图片数据已迁移至文件系统，通过 API 端点获取
            result["image_url"] = f"/image_reports/{self.report_id}/image"

        # 包含匹配详情
        if self.matching_details:
            result["matching_details"] = self.matching_details

        # safe模式：排除敏感/内部字段
        if safe:
            for field in self._SENSITIVE_FIELDS:
                result.pop(field, None)

        return result


class ImageCategory(Base):
    """图片分类表"""
    __tablename__ = "image_category"

    category_id = Column(Integer, primary_key=True, index=True)
    category_key = Column(String(50), unique=True, nullable=False, comment="分类key")
    category_name = Column(String(100), nullable=False, comment="分类名称")
    icon = Column(String(10), nullable=True, comment="图标")
    color = Column(String(20), nullable=True, comment="颜色")
    description = Column(String(200), nullable=True, comment="描述")
    sort_order = Column(Integer, default=0, comment="排序")
    is_active = Column(Boolean, default=True, comment="是否启用")
    group_key = Column(String(50), nullable=True, comment="分组标识")
    report_type = Column(String(20), nullable=True, comment="OCR报告类型: lab/exam/pathology")

    def to_dict(self):
        """转换为字典"""
        return {
            "category_id": self.category_id,
            "category_key": self.category_key,
            "category_name": self.category_name,
            "icon": self.icon,
            "color": self.color,
            "description": self.description,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            "group_key": self.group_key,
            "report_type": self.report_type
        }
