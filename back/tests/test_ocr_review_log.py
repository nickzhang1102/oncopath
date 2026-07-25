"""OCR审查日志模型单元测试"""
import pytest
from app.models.ocr_review_log import OCRReviewLog
from app.utils.time_utils import get_utc_now


def test_ocr_review_log_model_fields():
    """测试 OCRReviewLog 模型字段定义"""
    assert OCRReviewLog.__tablename__ == "ocr_review_logs"

    columns = {c.name for c in OCRReviewLog.__table__.columns}
    expected = {"id", "report_id", "report_type", "field_name",
                "original_value", "corrected_value", "reviewed_at"}
    assert columns == expected


def test_ocr_review_log_field_comments():
    """测试字段注释"""
    table = OCRReviewLog.__table__
    assert table.c.report_type.comment == "报告类型: lab/exam/pathology"
    assert table.c.field_name.comment == "被修正的字段名"
    assert table.c.original_value.comment == "OCR原始值"
    assert table.c.corrected_value.comment == "用户修正值"
    assert table.c.reviewed_at.comment == "审查时间"


def test_ocr_review_log_foreign_key():
    """测试外键关联"""
    fks = list(OCRReviewLog.__table__.foreign_keys)
    assert len(fks) == 1
    fk = fks[0]
    assert fk.target_fullname == "image_report.report_id"


def test_ocr_review_log_nullable():
    """测试字段可空性"""
    table = OCRReviewLog.__table__
    assert not table.c.report_id.nullable
    assert not table.c.report_type.nullable
    assert not table.c.field_name.nullable
    assert table.c.original_value.nullable
    assert table.c.corrected_value.nullable
    assert table.c.reviewed_at.nullable