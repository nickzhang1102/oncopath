"""用药记录模型单元测试"""
import pytest
from app.models.medication import Medication


class TestMedicationModel:
    """Medication 模型测试"""

    def test_table_name(self):
        assert Medication.__tablename__ == "medications"

    def test_required_fields(self):
        columns = {c.name for c in Medication.__table__.columns}
        required = {"id", "patient_id", "account_id", "medication_name", "start_date"}
        for field in required:
            assert field in columns, f"缺少必要字段: {field}"

    def test_optional_fields(self):
        columns = {c.name for c in Medication.__table__.columns}
        optional = {
            "generic_name", "dosage", "frequency", "route", "duration",
            "end_date", "prescriber", "hospital", "notes", "side_effects",
        }
        for field in optional:
            assert field in columns, f"缺少可选字段: {field}"

    def test_default_values(self):
        col_defaults = {c.name: c.default for c in Medication.__table__.columns}
        # source 默认 "manual"
        source_col = Medication.__table__.columns["source"]
        assert source_col.default is not None
        assert source_col.default.arg == "manual"
        # status 默认 "active"
        status_col = Medication.__table__.columns["status"]
        assert status_col.default is not None
        assert status_col.default.arg == "active"
        # is_ongoing 默认 True
        ongoing_col = Medication.__table__.columns["is_ongoing"]
        assert ongoing_col.default is not None
        assert ongoing_col.default.arg is True

    def test_foreign_keys(self):
        fks = {fk.target_fullname for fk in Medication.__table__.foreign_keys}
        assert "patient.patient_id" in fks
        assert "login_account.account_id" in fks

    def test_nullable_fields(self):
        nullable = {c.name for c in Medication.__table__.columns if c.nullable}
        assert "end_date" in nullable
        assert "generic_name" in nullable
        assert "dosage" in nullable
        assert "notes" in nullable
        assert "side_effects" in nullable

    def test_non_nullable_fields(self):
        non_nullable = {c.name for c in Medication.__table__.columns if not c.nullable}
        assert "patient_id" in non_nullable
        assert "account_id" in non_nullable
        assert "medication_name" in non_nullable
        assert "start_date" in non_nullable
