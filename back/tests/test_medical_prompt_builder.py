"""MedicalPromptBuilder 单元测试

测试截断阈值常量、全部指标输出、异常/正常标记、分类分组等功能。
"""

import pytest
from unittest.mock import MagicMock
from datetime import date

from app.services.consultation.medical_prompt_builder import MedicalPromptBuilder


@pytest.fixture
def builder():
    return MedicalPromptBuilder()


class TestClassConstants:
    """测试类常量"""

    def test_record_content_limit(self, builder):
        assert builder.RECORD_CONTENT_LIMIT == 1000

    def test_exam_findings_limit(self, builder):
        assert builder.EXAM_FINDINGS_LIMIT == 500

    def test_category_map(self, builder):
        assert builder.CATEGORY_MAP == {
            "blood_routine": "血常规",
            "biochemistry": "生化",
            "tumor_marker": "肿瘤标志物",
            "coagulation": "凝血",
            "urine_routine": "尿常规",
            "body_weight": "体重",
        }


class TestExtractAllCheckDetails:
    """测试 _extract_all_check_details 方法"""

    def _make_detail(self, index_name, index_value, index_unit, reference_value,
                     index_status, category=None, standard_name=None):
        """创建模拟的 MedicalCheckDetail"""
        detail = MagicMock()
        detail.index_name = index_name
        detail.index_value = index_value
        detail.index_unit = index_unit
        detail.reference_value = reference_value
        detail.index_status = index_status
        detail.medical_detail_id = 1

        if category or standard_name:
            standard_index = MagicMock()
            standard_index.category = category
            standard_index.index_name = standard_name or index_name
            detail.standard_index = standard_index
        else:
            detail.standard_index = None

        return detail

    def test_empty_details(self, builder):
        assert builder._extract_all_check_details([]) == []

    def test_includes_both_normal_and_abnormal(self, builder):
        """全部指标输出包含正常和异常"""
        normal_detail = self._make_detail("WBC", "5.0", "10^9/L", "3.5-9.5", "normal")
        abnormal_detail = self._make_detail("HGB", "110", "g/L", "130-175", "abnormal")

        result = builder._extract_all_check_details([normal_detail, abnormal_detail])
        assert len(result) == 2

    def test_abnormal_has_warning_prefix(self, builder):
        """异常指标有 ⚠ 前缀"""
        abnormal_detail = self._make_detail("HGB", "110", "g/L", "130-175", "abnormal")
        result = builder._extract_all_check_details([abnormal_detail])
        assert result[0]["mark"] == "⚠"

    def test_normal_has_no_warning_prefix(self, builder):
        """正常指标前缀为两空格"""
        normal_detail = self._make_detail("WBC", "5.0", "10^9/L", "3.5-9.5", "normal")
        result = builder._extract_all_check_details([normal_detail])
        assert result[0]["mark"] == "  "

    def test_detail_fields(self, builder):
        """检查输出字段完整性"""
        detail = self._make_detail("WBC", "5.0", "10^9/L", "3.5-9.5", "normal",
                                   category="blood_routine", standard_name="白细胞计数")
        result = builder._extract_all_check_details([detail])
        item = result[0]
        assert item["mark"] == "  "
        assert item["指标"] == "白细胞计数"
        assert item["值"] == "5.0"
        assert item["单位"] == "10^9/L"
        assert item["参考"] == "3.5-9.5"
        assert item["category"] == "血常规"

    def test_category_default_is_other(self, builder):
        """无 standard_index 时分类默认为 其他"""
        detail = self._make_detail("WBC", "5.0", "10^9/L", "3.5-9.5", "normal")
        result = builder._extract_all_check_details([detail])
        assert result[0]["category"] == "其他"

    def test_category_unknown_code(self, builder):
        """未知分类代码保留原值"""
        detail = self._make_detail("XYZ", "1.0", "mg", "0-5", "normal",
                                   category="unknown_category")
        result = builder._extract_all_check_details([detail])
        assert result[0]["category"] == "unknown_category"

    def test_prefer_cn_name_over_index_name(self, builder):
        """优先使用标准指标中文名称"""
        detail = self._make_detail("WBC", "5.0", "10^9/L", "3.5-9.5", "normal",
                                   category="blood_routine", standard_name="白细胞计数")
        result = builder._extract_all_check_details([detail])
        assert result[0]["指标"] == "白细胞计数"


class TestCategoryGrouping:
    """测试分类分组输出"""

    def test_format_prompt_groups_by_category(self, builder):
        """当前配置驱动格式按分类筛选并保留异常标记。"""
        check = MagicMock(medical_date=date.today())
        blood = TestExtractAllCheckDetails()._make_detail(
            "HGB", "110", "g/L", "130-175", "abnormal", "blood_routine"
        )
        chemistry = TestExtractAllCheckDetails()._make_detail(
            "GLU", "8.5", "mmol/L", "3.9-6.1", "abnormal", "biochemistry"
        )
        blood.standard_index.sort = 1
        chemistry.standard_index.sort = 2
        check.details = [blood, chemistry]
        patient = MagicMock(medical_checks=[check])

        output = builder._format_lab_by_category(patient, "blood_routine")

        assert "HGB：↑110 g/L" in output
        assert "GLU" not in output


class TestTruncationLimits:
    """测试截断阈值"""

    def test_record_content_truncated_at_1000(self, builder):
        """病情记录内容超过 1000 字符时截断"""
        long_content = "A" * 1500
        record = MagicMock(
            record_date=date.today(), record_name="测试", record_type="门诊",
            patient_status=None, record_info=long_content, record_drug=None,
            hospital=None,
        )
        patient = MagicMock(medical_records=[record])
        prompt = builder._format_medical_records(patient, content_limit=1000)

        # 截断后的内容 + "..." = 1003 字符
        assert ("A" * 1000 + "...") in prompt
        assert "A" * 1001 not in prompt  # 超出部分不在

    def test_exam_findings_truncated_at_500(self, builder):
        """检查报告影像所见超过 500 字符时截断"""
        long_finding = "B" * 800
        exam = MagicMock(
            medical_date=date.today(), title="CT报告", exam_type="CT",
            exam_info=long_finding, exam_diag="未见异常",
        )
        patient = MagicMock(medical_exams=[exam])
        prompt = builder._format_exams(patient, findings_limit=500)

        assert ("B" * 500 + "...") in prompt


class TestPromptLengthWarning:
    """测试提示词长度警告"""

    @pytest.mark.asyncio
    async def test_warning_logged_for_long_prompt(self, builder, caplog):
        """超过 30000 字符时记录警告日志"""
        import logging
        with caplog.at_level(logging.WARNING, logger="app.services.consultation.medical_prompt_builder"):
            # 构造超长内容
            long_content = "X" * 31000
            prompt = await builder._format_prompt_config_driven(
                patient=MagicMock(),
                config_items=[{
                    "name": "自定义内容", "type": "custom", "enabled": True,
                    "customText": long_content,
                }],
            )
            assert len(prompt) <= 30050
            assert "exceeds 30000 chars" in caplog.text

    @pytest.mark.asyncio
    async def test_no_warning_for_normal_prompt(self, builder, caplog):
        """正常长度不记录警告"""
        import logging
        with caplog.at_level(logging.WARNING, logger="app.services.consultation.medical_prompt_builder"):
            await builder._format_prompt_config_driven(
                patient=MagicMock(),
                config_items=[{
                    "name": "自定义内容", "type": "custom", "enabled": True,
                    "customText": "正常长度",
                }],
            )
            assert "exceeds 30000 chars" not in caplog.text


from app.services.consultation.medical_prompt_builder import MedicalPromptBuilder, DEFAULT_USER_CONTENT_CONFIG


class TestConfigDrivenPrompt:
    """测试配置驱动提示词构建"""

    def test_default_config_has_18_items(self):
        """默认配置应有18项"""
        assert len(DEFAULT_USER_CONTENT_CONFIG) == 18

    def test_default_config_enabled_count(self):
        """默认配置中至少10项启用"""
        enabled_count = sum(1 for item in DEFAULT_USER_CONTENT_CONFIG if item.get("enabled", True))
        assert enabled_count >= 10

    @pytest.mark.asyncio
    async def test_disabled_item_excluded(self, builder):
        """禁用项不应出现在提示词中"""
        patient = MagicMock()
        patient.medical_history = "高血压"
        patient.timeline_events = []
        patient.pathology_reports = []
        patient.medical_checks = []
        patient.medical_exams = []
        patient.medical_records = []

        config = [
            {"name": "病史记录", "type": "history", "enabled": True},
            {"name": "治疗时间线", "type": "timeline", "enabled": False, "recentCount": 20},
        ]
        prompt = await builder._format_prompt_config_driven(patient=patient, config_items=config)
        assert "病史记录" in prompt
        assert "治疗时间线" not in prompt

    @pytest.mark.asyncio
    async def test_custom_type_with_text(self, builder):
        """custom 类型应输出 customText"""
        patient = MagicMock()
        config = [
            {"name": "诊断要求", "type": "custom", "enabled": True, "customText": "请提供治疗建议"},
        ]
        prompt = await builder._format_prompt_config_driven(patient=patient, config_items=config)
        assert "请提供治疗建议" in prompt

    @pytest.mark.asyncio
    async def test_custom_type_empty_text_excluded(self, builder):
        """custom 类型 customText 为空时应跳过"""
        patient = MagicMock()
        config = [
            {"name": "自定义内容", "type": "custom", "enabled": True, "customText": ""},
        ]
        prompt = await builder._format_prompt_config_driven(patient=patient, config_items=config)
        assert "自定义内容" not in prompt

    @pytest.mark.asyncio
    async def test_diagnostic_requirement_replaces_default_footer(self, builder):
        """有诊断要求时不再追加默认footer"""
        patient = MagicMock()
        config = [
            {"name": "诊断要求", "type": "custom", "enabled": True, "customText": "请提供治疗建议"},
        ]
        prompt = await builder._format_prompt_config_driven(patient=patient, config_items=config)
        assert "请基于以上患者资料，提供专业的会诊意见" not in prompt


class TestFormatSummaryOrFallback:
    """测试 _format_summary_or_fallback 概要优先+降级逻辑"""

    @pytest.mark.asyncio
    async def test_no_db_falls_back(self, builder):
        """无 db 时直接降级到 fallback"""
        patient = MagicMock()
        result = await builder._format_summary_or_fallback(
            patient=patient,
            db=None,
            summary_type="treatment",
            fallback_fn=lambda: "逐条治疗记录",
        )
        assert result == "逐条治疗记录"

    @pytest.mark.asyncio
    async def test_has_summary_returns_summary(self, builder):
        """有概要时返回概要文本"""
        from unittest.mock import AsyncMock
        patient = MagicMock()
        patient.patient_id = 1

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # mock SummaryService.get_summaries_text
        import unittest.mock as umock
        with umock.patch(
            "app.services.consultation.summary_service.SummaryService.get_summaries_text",
            new_callable=AsyncMock,
            return_value="概要文本：2026年1-4月化疗4周期",
        ):
            result = await builder._format_summary_or_fallback(
                patient=patient,
                db=mock_db,
                summary_type="treatment",
                fallback_fn=lambda: "逐条记录",
            )
        assert result == "概要文本：2026年1-4月化疗4周期"

    @pytest.mark.asyncio
    async def test_no_summary_falls_back(self, builder):
        """无概要时降级到 fallback"""
        from unittest.mock import AsyncMock
        patient = MagicMock()
        patient.patient_id = 1

        mock_db = AsyncMock()

        import unittest.mock as umock
        with umock.patch(
            "app.services.consultation.summary_service.SummaryService.get_summaries_text",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await builder._format_summary_or_fallback(
                patient=patient,
                db=mock_db,
                summary_type="medication_record",
                fallback_fn=lambda: "逐条用药记录",
            )
        assert result == "逐条用药记录"
