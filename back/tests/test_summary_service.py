"""SummaryService 单元测试

测试规则模板拼接（治疗/用药）和 CRUD 基本逻辑。
"""
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from app.services.consultation.summary_service import SummaryService


@pytest.fixture
def mock_db():
    """模拟 AsyncSession — execute/flush 为 AsyncMock，add/delete 为同步 MagicMock"""
    db = AsyncMock()
    db.add = MagicMock()
    db.delete = MagicMock()
    return db


@pytest.fixture
def service(mock_db):
    return SummaryService(db=mock_db)


def _mock_result(scalars_all=None, scalar_one_or_none=None):
    """构造 execute 返回的 result mock，支持链式 .scalars().all() 和 .scalar_one_or_none()"""
    result = MagicMock()
    if scalars_all is not None:
        result.scalars.return_value.all.return_value = scalars_all
    if scalar_one_or_none is not None:
        result.scalar_one_or_none.return_value = scalar_one_or_none
    return result


def _make_treatment_event(event_date, category, title, description=None):
    """创建模拟的 TimelineEvent（治疗类）"""
    event = MagicMock()
    event.event_date = event_date
    event.category = category
    event.event_type = "medical"
    event.title = title
    event.description = description
    return event


def _make_medication(
    medication_name, start_date, dosage=None, frequency=None,
    route=None, end_date=None, status="active", notes=None, side_effects=None,
):
    """创建模拟的 Medication"""
    med = MagicMock()
    med.medication_name = medication_name
    med.start_date = start_date
    med.dosage = dosage
    med.frequency = frequency
    med.route = route
    med.end_date = end_date
    med.status = status
    med.notes = notes
    med.side_effects = side_effects
    return med


def _make_summary(summary_id, summary_type, period_start, period_end,
                  summary_text, source="rule_template", status="draft",
                  source_record_count=1):
    """创建模拟的 RecordSummary"""
    s = MagicMock()
    s.summary_id = summary_id
    s.summary_type = summary_type
    s.period_start = period_start
    s.period_end = period_end
    s.summary_text = summary_text
    s.source = source
    s.status = status
    s.source_record_count = source_record_count
    return s


class TestTreatmentRuleSummary:
    """治疗记录规则模板拼接"""

    @pytest.mark.asyncio
    async def test_single_chemotherapy(self, service, mock_db):
        events = [_make_treatment_event(
            date(2026, 1, 15), "chemotherapy", "吉西他滨+白蛋白紫杉醇化疗",
            description="4周期",
        )]
        mock_db.execute.return_value = _mock_result(scalars_all=events)

        text, count = await service._generate_treatment_summary(
            patient_id=1,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 4, 30),
        )
        assert count == 1
        assert "2026-01-15" in text
        assert "吉西他滨+白蛋白紫杉醇化疗" in text
        assert "4周期" in text

    @pytest.mark.asyncio
    async def test_multiple_events_sorted(self, service, mock_db):
        events = [
            _make_treatment_event(date(2026, 5, 10), "surgery", "胰腺癌根治术"),
            _make_treatment_event(date(2026, 1, 15), "chemotherapy", "吉西他滨化疗", "4周期"),
        ]
        mock_db.execute.return_value = _mock_result(scalars_all=events)

        text, count = await service._generate_treatment_summary(
            patient_id=1,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 6, 30),
        )
        assert count == 2
        lines = text.split("\n")
        assert len(lines) == 2

    @pytest.mark.asyncio
    async def test_no_events_in_period(self, service, mock_db):
        mock_db.execute.return_value = _mock_result(scalars_all=[])

        text, count = await service._generate_treatment_summary(
            patient_id=1,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 4, 30),
        )
        assert count == 0
        assert text == ""


class TestMedicationRuleSummary:
    """用药记录规则模板拼接"""

    @pytest.mark.asyncio
    async def test_active_medication(self, service, mock_db):
        meds = [_make_medication(
            "卡培他滨", date(2026, 5, 1),
            dosage="1500mg", route="口服", frequency="每日2次",
            status="active",
        )]
        mock_db.execute.return_value = _mock_result(scalars_all=meds)

        text, count = await service._generate_medication_summary(
            patient_id=1,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 8, 31),
        )
        assert count == 1
        assert "卡培他滨" in text
        assert "1500mg" in text
        assert "口服" in text
        assert "持续中" in text

    @pytest.mark.asyncio
    async def test_discontinued_medication(self, service, mock_db):
        meds = [_make_medication(
            "奥施康定", date(2026, 1, 1),
            end_date=date(2026, 3, 15),
            status="discontinued",
            side_effects="便秘",
        )]
        mock_db.execute.return_value = _mock_result(scalars_all=meds)

        text, count = await service._generate_medication_summary(
            patient_id=1,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 4, 30),
        )
        assert count == 1
        assert "停药" in text
        assert "奥施康定" in text
        assert "便秘" in text

    @pytest.mark.asyncio
    async def test_mixed_medications(self, service, mock_db):
        meds = [
            _make_medication(
                "吉西他滨", date(2026, 1, 1),
                dosage="1000mg/m2", route="静脉",
                end_date=date(2026, 4, 1), status="completed",
            ),
            _make_medication(
                "卡培他滨", date(2026, 5, 1),
                dosage="1500mg", route="口服", frequency="每日2次",
                status="active",
            ),
        ]
        mock_db.execute.return_value = _mock_result(scalars_all=meds)

        text, count = await service._generate_medication_summary(
            patient_id=1,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 8, 31),
        )
        assert count == 2

    @pytest.mark.asyncio
    async def test_no_medications_in_period(self, service, mock_db):
        mock_db.execute.return_value = _mock_result(scalars_all=[])

        text, count = await service._generate_medication_summary(
            patient_id=1,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 4, 30),
        )
        assert count == 0
        assert text == ""


class TestUpsertRuleSummary:
    """upsert 规则概要（confirmed 保护）"""

    @pytest.mark.asyncio
    async def test_create_new_summary(self, service, mock_db):
        mock_db.execute.return_value = _mock_result(scalar_one_or_none=None)

        result = await service.upsert_rule_summary(
            patient_id=1,
            summary_type="treatment",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 4, 30),
            summary_text="测试概要",
            source_record_count=3,
        )
        assert result is not None
        mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_overwrite_draft(self, service, mock_db):
        existing = _make_summary(
            1, "treatment", date(2026, 1, 1), date(2026, 4, 30),
            "旧概要", status="draft",
        )
        mock_db.execute.return_value = _mock_result(scalar_one_or_none=existing)

        result = await service.upsert_rule_summary(
            patient_id=1,
            summary_type="treatment",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 4, 30),
            summary_text="新概要",
            source_record_count=5,
        )
        assert result.summary_text == "新概要"

    @pytest.mark.asyncio
    async def test_protect_confirmed(self, service, mock_db):
        existing = _make_summary(
            1, "treatment", date(2026, 1, 1), date(2026, 4, 30),
            "已确认概要", status="confirmed",
        )
        mock_db.execute.return_value = _mock_result(scalar_one_or_none=existing)

        result = await service.upsert_rule_summary(
            patient_id=1,
            summary_type="treatment",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 4, 30),
            summary_text="新概要",
            source_record_count=5,
        )
        assert result.summary_text == "已确认概要"


class TestGetSummariesText:
    """概要文本读取（供 prompt builder 使用）"""

    @pytest.mark.asyncio
    async def test_has_summaries(self, service, mock_db):
        s1 = _make_summary(1, "treatment", date(2026, 1, 1), date(2026, 4, 30), "概要1")
        s2 = _make_summary(2, "treatment", date(2026, 5, 1), date(2026, 8, 31), "概要2")
        mock_db.execute.return_value = _mock_result(scalars_all=[s1, s2])

        text = await service.get_summaries_text(patient_id=1, summary_type="treatment")
        assert text == "概要1\n概要2"

    @pytest.mark.asyncio
    async def test_no_summaries(self, service, mock_db):
        mock_db.execute.return_value = _mock_result(scalars_all=[])

        text = await service.get_summaries_text(patient_id=1, summary_type="treatment")
        assert text is None


class TestLLMSummary:
    """LLM 摘要生成（状态记录）"""

    @pytest.mark.asyncio
    async def test_generate_llm_summary_success(self, service, mock_db):
        """mock LLM 返回 → 摘要写入 record_summary"""
        # 模拟状态记录
        events = []
        for i, (d, title) in enumerate([
            (date(2026, 1, 5), "状态一般"),
            (date(2026, 1, 10), "略有好转"),
        ]):
            event = MagicMock()
            event.event_date = d
            event.category = "daily_status"
            event.title = title
            event.description = None
            event.life_details = None
            events.append(event)

        # 第一次 execute 返回状态记录，第二次返回 None（无已有概要）
        call_count = 0

        def mock_execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalars.return_value.all.return_value = events
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute.side_effect = mock_execute_side_effect

        # mock LLM
        llm = AsyncMock()
        llm.chat.return_value = "患者1月上旬状态一般，中旬略有好转。"

        result = await service.generate_llm_summary(
            patient_id=1,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            llm_service=llm,
        )
        assert result is not None
        assert result.source == "llm_generated"
        assert result.status == "draft"
        llm.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_llm_summary_no_records(self, service, mock_db):
        """无状态记录时返回 None"""
        mock_db.execute.return_value = _mock_result(scalars_all=[])

        llm = AsyncMock()
        result = await service.generate_llm_summary(
            patient_id=1,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            llm_service=llm,
        )
        assert result is None
        llm.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_llm_summary_no_service(self, service, mock_db):
        """未注入 llm_service 时返回 None"""
        result = await service.generate_llm_summary(
            patient_id=1,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        assert result is None
