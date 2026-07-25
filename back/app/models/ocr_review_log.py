"""OCR审查日志模型 - 记录用户对OCR结果的修正"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.time_utils import get_utc_now


class OCRReviewLog(Base):
    """OCR审查日志表"""
    __tablename__ = "ocr_review_logs"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("image_report.report_id"), nullable=False, comment="报告ID")
    report_type = Column(String(20), nullable=False, comment="报告类型: lab/exam/pathology")
    field_name = Column(String(100), nullable=False, comment="被修正的字段名")
    original_value = Column(Text, nullable=True, comment="OCR原始值")
    corrected_value = Column(Text, nullable=True, comment="用户修正值")
    reviewed_at = Column(DateTime, default=get_utc_now, comment="审查时间")

    # 关系
    image_report = relationship("ImageReport", back_populates="review_logs")