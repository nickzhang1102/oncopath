"""记录概要摘要服务

提供概要的 CRUD、规则模板拼接（用药/治疗）、LLM 摘要生成（状态记录）。
"""
import logging
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import select, and_, or_, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.record_summary import RecordSummary
from app.models.medication import Medication
from app.models.timeline import TimelineEvent

logger = logging.getLogger(__name__)

# 治疗类事件 category 集合（与 medical_prompt_builder 保持一致）
TREATMENT_CATEGORIES = {
    "chemotherapy", "radiation", "surgery", "targeted",
    "immunotherapy", "adc", "car_t",
}

CATEGORY_LABELS = {
    "chemotherapy": "化疗",
    "radiation": "放疗",
    "surgery": "手术",
    "targeted": "靶向",
    "immunotherapy": "免疫",
    "adc": "ADC",
    "car_t": "CAR-T",
}


class SummaryService:
    """记录概要摘要服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---- CRUD ----

    async def list_summaries(
        self,
        patient_id: int,
        summary_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[RecordSummary]:
        """查询概要列表"""
        conditions = [RecordSummary.patient_id == patient_id]
        if summary_type:
            conditions.append(RecordSummary.summary_type == summary_type)
        if status:
            conditions.append(RecordSummary.status == status)

        stmt = (
            select(RecordSummary)
            .where(and_(*conditions))
            .order_by(RecordSummary.period_start)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_summary(self, summary_id: int) -> Optional[RecordSummary]:
        """获取单条概要"""
        stmt = select(RecordSummary).where(RecordSummary.summary_id == summary_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_summary(self, **kwargs) -> RecordSummary:
        """创建概要"""
        summary = RecordSummary(**kwargs)
        self.db.add(summary)
        await self.db.flush()
        return summary

    async def update_summary(
        self,
        summary_id: int,
        summary_text: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[RecordSummary]:
        """更新概要（编辑/确认）"""
        summary = await self.get_summary(summary_id)
        if not summary:
            return None
        if summary_text is not None:
            summary.summary_text = summary_text
        if status is not None:
            summary.status = status
        await self.db.flush()
        return summary

    async def delete_summary(self, summary_id: int) -> bool:
        """删除概要"""
        summary = await self.get_summary(summary_id)
        if not summary:
            return False
        await self.db.delete(summary)
        await self.db.flush()
        return True

    async def upsert_rule_summary(
        self,
        patient_id: int,
        summary_type: str,
        period_start: date,
        period_end: date,
        summary_text: str,
        source_record_count: int,
    ) -> RecordSummary:
        """写入或覆盖规则模板概要（仅覆盖 draft，confirmed 不动）"""
        stmt = select(RecordSummary).where(
            and_(
                RecordSummary.patient_id == patient_id,
                RecordSummary.summary_type == summary_type,
                RecordSummary.period_start == period_start,
                RecordSummary.period_end == period_end,
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            if existing.status == "confirmed":
                return existing
            existing.summary_text = summary_text
            existing.source = "rule_template"
            existing.source_record_count = source_record_count
            await self.db.flush()
            return existing

        summary = RecordSummary(
            patient_id=patient_id,
            summary_type=summary_type,
            period_start=period_start,
            period_end=period_end,
            summary_text=summary_text,
            source="rule_template",
            status="draft",
            source_record_count=source_record_count,
        )
        self.db.add(summary)
        await self.db.flush()
        return summary

    # ---- 规则模板拼接 ----

    async def generate_rule_summary(
        self,
        patient_id: int,
        summary_type: str,
        period_start: date,
        period_end: date,
    ) -> Optional[RecordSummary]:
        """根据时段查询原始记录，规则模板拼接生成概要

        Args:
            patient_id: 患者ID
            summary_type: treatment 或 medication_record
            period_start: 时段起始
            period_end: 时段结束
        """
        if summary_type == "treatment":
            summary_text, count = await self._generate_treatment_summary(
                patient_id, period_start, period_end
            )
        elif summary_type == "medication_record":
            summary_text, count = await self._generate_medication_summary(
                patient_id, period_start, period_end
            )
        else:
            logger.warning("不支持的规则模板类型: %s", summary_type)
            return None

        if not summary_text or count == 0:
            return None

        return await self.upsert_rule_summary(
            patient_id=patient_id,
            summary_type=summary_type,
            period_start=period_start,
            period_end=period_end,
            summary_text=summary_text,
            source_record_count=count,
        )

    async def _generate_treatment_summary(
        self,
        patient_id: int,
        period_start: date,
        period_end: date,
    ) -> tuple[str, int]:
        """治疗记录规则模板拼接

        格式示例：
        2026-01-15 至 2026-04-20：吉西他滨+白蛋白紫杉醇化疗4周期
        2026-05-10：胰腺癌根治术
        """
        stmt = (
            select(TimelineEvent)
            .where(
                and_(
                    TimelineEvent.patient_id == patient_id,
                    TimelineEvent.event_type == "medical",
                    TimelineEvent.category.in_(TREATMENT_CATEGORIES),
                    TimelineEvent.event_date >= period_start,
                    TimelineEvent.event_date <= period_end,
                )
            )
            .order_by(TimelineEvent.event_date)
        )
        result = await self.db.execute(stmt)
        events = list(result.scalars().all())

        if not events:
            return "", 0

        lines = []
        for event in events:
            date_str = event.event_date.strftime("%Y-%m-%d") if event.event_date else "未知"
            cat_label = CATEGORY_LABELS.get(event.category, event.category)
            line = f"{date_str}：{event.title or cat_label}"
            if event.description:
                line += f"（{event.description}）"
            lines.append(line)

        return "\n".join(lines), len(events)

    async def _generate_medication_summary(
        self,
        patient_id: int,
        period_start: date,
        period_end: date,
    ) -> tuple[str, int]:
        """用药记录规则模板拼接

        格式示例：
        2026-01 至 2026-04：吉西他滨 1000mg/m2 静脉 d1,d8 + 白蛋白紫杉醇 125mg/m2 静脉 d1,d8,d15（4周期）
        2026-05 至今：卡培他滨 1500mg 口服 每日2次（持续中）
        停药：奥施康定 2026-03-15（副作用：便秘）
        """
        stmt = (
            select(Medication)
            .where(
                and_(
                    Medication.patient_id == patient_id,
                    Medication.start_date <= period_end,
                    or_(
                        Medication.end_date.is_(None),
                        Medication.end_date >= period_start,
                    ),
                )
            )
            .order_by(Medication.start_date)
        )
        result = await self.db.execute(stmt)
        medications = list(result.scalars().all())

        if not medications:
            return "", 0

        active_lines = []
        discontinued_lines = []

        for med in medications:
            start_str = med.start_date.strftime("%Y-%m") if med.start_date else "未知"
            if med.status == "active" or med.end_date is None:
                end_str = "至今"
            else:
                end_str = med.end_date.strftime("%Y-%m")

            parts = [med.medication_name]
            if med.dosage:
                parts.append(med.dosage)
            if med.route:
                parts.append(med.route)
            if med.frequency:
                parts.append(med.frequency)

            period_str = f"{start_str} {end_str}：" if start_str != end_str else f"{start_str}："
            status_tag = "（持续中）" if med.status == "active" else ""

            if med.status != "active":
                discontinue_date = med.end_date.strftime("%Y-%m-%d") if med.end_date else ""
                reason = ""
                if med.notes and "停药原因" in med.notes:
                    reason = med.notes.split("停药原因:")[-1].strip().split("\n")[0]
                side_effect = f"（副作用：{med.side_effects}）" if med.side_effects else ""
                discontinued_lines.append(
                    f"停药：{med.medication_name} {discontinue_date}{side_effect}"
                    + (f"（{reason}）" if reason else "")
                )
            else:
                active_lines.append(f"{period_str}{' '.join(parts)}{status_tag}")

        lines = active_lines + discontinued_lines
        return "\n".join(lines), len(medications)

    # ---- LLM 摘要生成（状态记录）----

    STATUS_SUMMARY_SYSTEM_PROMPT = (
        "你是一位专业的医疗助手。请根据患者的状态记录，生成一段简洁的概要摘要。"
        "要求：\n"
        "1. 用自然语言概括该时段内的整体状态趋势\n"
        "2. 突出重要变化（如疼痛加重/缓解、情绪波动、睡眠改善等）\n"
        "3. 保留关键评分数据（如疼痛评分从X降至Y）\n"
        "4. 200字以内\n"
        "5. 不要列出每一天的记录，而是总结趋势和关键节点\n"
        "6. 用中文输出"
    )

    async def generate_llm_summary(
        self,
        patient_id: int,
        period_start: date,
        period_end: date,
        llm_service=None,
    ) -> Optional[RecordSummary]:
        """LLM 生成状态记录概要

        查询指定时段状态记录 → 拼接输入 → 调用 LLM → 写入 record_summary

        Args:
            patient_id: 患者ID
            period_start: 时段起始
            period_end: 时段结束
            llm_service: LLMService 实例（由调用方注入）
        """
        if not llm_service:
            logger.warning("generate_llm_summary 需要注入 llm_service")
            return None

        # 查询状态记录
        status_text, count = await self._collect_status_records(
            patient_id, period_start, period_end
        )
        if count == 0:
            return None

        # 调用 LLM
        try:
            summary_text = await llm_service.chat(
                system_prompt=self.STATUS_SUMMARY_SYSTEM_PROMPT,
                user_message=f"请概括以下 {period_start} 至 {period_end} 的患者状态记录：\n\n{status_text}",
                max_tokens=500,
            )
        except Exception as e:
            logger.error("LLM 生成状态概要失败: %s", e)
            return None

        if not summary_text or not summary_text.strip():
            return None

        # 写入 record_summary（draft），confirmed 概要不覆盖
        stmt = select(RecordSummary).where(
            and_(
                RecordSummary.patient_id == patient_id,
                RecordSummary.summary_type == "status",
                RecordSummary.period_start == period_start,
                RecordSummary.period_end == period_end,
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            if existing.status == "confirmed":
                return existing
            existing.summary_text = summary_text.strip()
            existing.source = "llm_generated"
            existing.source_record_count = count
            await self.db.flush()
            return existing

        summary = RecordSummary(
            patient_id=patient_id,
            summary_type="status",
            period_start=period_start,
            period_end=period_end,
            summary_text=summary_text.strip(),
            source="llm_generated",
            status="draft",
            source_record_count=count,
        )
        self.db.add(summary)
        await self.db.flush()
        return summary

    async def _collect_status_records(
        self,
        patient_id: int,
        period_start: date,
        period_end: date,
    ) -> tuple[str, int]:
        """收集时段内状态记录，拼接为 LLM 输入文本"""
        stmt = (
            select(TimelineEvent)
            .where(
                and_(
                    TimelineEvent.patient_id == patient_id,
                    TimelineEvent.category == "daily_status",
                    TimelineEvent.event_date >= period_start,
                    TimelineEvent.event_date <= period_end,
                )
            )
            .order_by(TimelineEvent.event_date)
        )
        result = await self.db.execute(stmt)
        events = list(result.scalars().all())

        if not events:
            return "", 0

        lines = []
        for event in events:
            date_str = event.event_date.strftime("%Y-%m-%d") if event.event_date else "未知"
            line = f"{date_str}"
            if event.title:
                line += f" {event.title}"
            details = event.life_details if hasattr(event, 'life_details') else None
            if details and isinstance(details, dict):
                score_parts = []
                for key in ["mood", "pain", "sleep", "diet", "stool"]:
                    if key in details:
                        val = details[key]
                        if isinstance(val, dict) and "score" in val:
                            score_parts.append(f"{key}:{val['score']}")
                        elif isinstance(val, (int, float)):
                            score_parts.append(f"{key}:{val}")
                if score_parts:
                    line += f" [{', '.join(score_parts)}]"
                if "general_memo" in details and details["general_memo"]:
                    line += f" {details['general_memo']}"
            elif event.description:
                line += f" {event.description}"
            lines.append(line)

        return "\n".join(lines), len(events)

    # ---- 概要读取（供 prompt builder 使用）----

    async def get_summaries_text(
        self,
        patient_id: int,
        summary_type: str,
    ) -> Optional[str]:
        """获取某类型概要的拼接文本（供会诊提示词使用）

        查询 confirmed + draft 概要，按时段排序拼接。
        无概要时返回 None（调用方负责降级）。
        """
        stmt = (
            select(RecordSummary)
            .where(
                and_(
                    RecordSummary.patient_id == patient_id,
                    RecordSummary.summary_type == summary_type,
                    RecordSummary.status.in_(["confirmed", "draft"]),
                )
            )
            .order_by(RecordSummary.period_start)
        )
        result = await self.db.execute(stmt)
        summaries = list(result.scalars().all())

        if not summaries:
            return None

        return "\n".join(s.summary_text for s in summaries)
