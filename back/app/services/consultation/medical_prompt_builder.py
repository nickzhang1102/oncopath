"""医疗提示词构建器

负责组装完整的患者病历数据，为会诊提供全面的上下文信息。
"""

from typing import Optional
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.time_utils import get_utc_now
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload

from app.models.patient import Patient
from app.models.medical import MedicalCheck, MedicalCheckDetail, MedicalExam, PathologyReport, MedicalRecord
from app.models.timeline import TimelineEvent
from app.models.medication import Medication

DEFAULT_USER_CONTENT_CONFIG = [
    {"name": "自定义内容", "type": "custom", "enabled": False, "customText": ""},
    {"name": "病人概况", "type": "info", "enabled": True},
    {"name": "病史记录", "type": "history", "enabled": True},
    {"name": "治疗时间线", "type": "timeline", "enabled": False, "recentCount": 20},
    {"name": "病理报告", "type": "pathology", "enabled": True},
    {"name": "血常规", "type": "lab", "enabled": True, "indicatorCount": 7, "recentCount": 3, "category": "blood_routine"},
    {"name": "肿瘤指标", "type": "lab", "enabled": True, "indicatorCount": 10, "recentCount": 4, "category": "tumor_marker"},
    {"name": "生化指标", "type": "lab", "enabled": True, "indicatorCount": 27, "recentCount": 1, "category": "biochemistry"},
    {"name": "凝血指标", "type": "lab", "enabled": True, "indicatorCount": 7, "recentCount": 1, "category": "coagulation"},
    {"name": "体重记录", "type": "lab", "enabled": True, "indicatorCount": 2, "recentCount": 3, "category": "body_weight"},
    {"name": "尿常规", "type": "lab", "enabled": False, "indicatorCount": 10, "recentCount": 1, "category": "urine_routine"},
    {"name": "CT/检查报告", "type": "exam", "enabled": True, "recentCount": 2, "findingsLimit": 500},
    {"name": "治疗记录", "type": "treatment", "enabled": True, "recentCount": 10},
    {"name": "用药记录", "type": "medication_record", "enabled": True, "recentCount": 20},
    {"name": "状态记录", "type": "status", "enabled": True, "recentCount": 30, "contentLimit": 500},
    {"name": "当前用药方案", "type": "medication", "enabled": True},
    {"name": "用户补充说明", "type": "custom", "enabled": True, "customText": ""},
    {"name": "诊断要求", "type": "custom", "enabled": True, "customText": "请根据以上信息，提供：1. 当前病情分析 2. 诊断意见 3. 后续治疗建议 4. 注意事项"},
]


class MedicalPromptBuilder:
    """医疗提示词构建器

    负责从数据库中提取患者信息，并按照以下层次组装：
    1. 基础信息（患者基本信息 + 病史 + 治疗时间线）
    2. 基础报告（最新基因检测 + 免疫组化 + 病理报告）
    3. 近期报告（近2个月的检验 + 检查报告）
    """

    # 单条记录的展示阈值
    RECORD_CONTENT_LIMIT = 1000
    EXAM_FINDINGS_LIMIT = 500

    # 分类中文映射
    CATEGORY_MAP = {
        "blood_routine": "血常规",
        "biochemistry": "生化",
        "tumor_marker": "肿瘤标志物",
        "coagulation": "凝血",
        "urine_routine": "尿常规",
        "body_weight": "体重",
    }

    def __init__(self):
        self.timeframe_days = 60  # 近期报告时间范围（天）

    @staticmethod
    def _to_chinese_num(n: int) -> str:
        """数字转中文序号"""
        nums = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
                "十一", "十二", "十三", "十四", "十五"]
        return nums[n - 1] if 1 <= n <= len(nums) else str(n)

    async def build_consultation_prompt(
        self,
        patient_id: int,
        db: AsyncSession,
        user_message: Optional[str] = None,
        prompt_config: Optional[dict] = None,
    ) -> str:
        """组装完整的会诊提示词（配置驱动版本）

        Args:
            patient_id: 患者ID
            db: 数据库会话
            user_message: 用户附加说明（可选）
            prompt_config: 提示词配置（可选），含 user_content_config 列表。
                           无则使用 DEFAULT_USER_CONTENT_CONFIG。

        Returns:
            完整的医疗上下文提示词
        """
        # Batch load patient data (same as before)
        result = await db.execute(
            select(Patient)
            .where(Patient.patient_id == patient_id)
            .options(
                selectinload(Patient.medical_checks).selectinload(MedicalCheck.details).selectinload(MedicalCheckDetail.standard_index),
                selectinload(Patient.medical_exams),
                selectinload(Patient.pathology_reports).selectinload(PathologyReport.ihc_markers),
                selectinload(Patient.timeline_events),
                selectinload(Patient.medical_records),
                selectinload(Patient.medications),
            )
        )
        patient = result.scalar_one_or_none()

        if not patient:
            return ""

        # Determine config
        config_items = None
        if prompt_config:
            config_items = prompt_config.get("user_content_config")
            self.timeframe_days = prompt_config.get("time_range_days", 60)
        if not config_items:
            config_items = DEFAULT_USER_CONTENT_CONFIG

        # Use config-driven building
        prompt = await self._format_prompt_config_driven(
            patient=patient,
            config_items=config_items,
            user_message=user_message,
            db=db,
        )

        return prompt

    def _extract_basic_info(self, patient: Patient) -> dict:
        """从患者对象提取基础信息（脱敏后用于 LLM prompt）

        Args:
            patient: 患者对象

        Returns:
            患者基础信息字典（敏感字段已脱敏）
        """
        from app.services.desensitization import desensitization_service
        patient_data = patient.to_dict()
        info = {
            "姓名": desensitization_service.mask_name(patient_data["patient_name"] or ""),
            "性别": self._translate_gender(patient.gender),
            "年龄": self._calculate_age(patient.birth_date) if patient.birth_date else "未填写",
            "联系电话": desensitization_service.mask_phone(patient_data["patient_phone"] or ""),
            "身份证号": desensitization_service.mask_id_card(patient_data["id_card"] or ""),
        }
        if patient.allergies:
            info["过敏史"] = patient.allergies
        if patient.current_medications:
            info["当前用药"] = patient.current_medications
        return info

    def _format_basic_info(self, patient: Patient) -> str:
        """格式化病人概况（含姓名、性别、年龄、病史、过敏史）"""
        from app.services.desensitization import desensitization_service
        patient_data = patient.to_dict()
        lines = []
        info_pairs = [
            ("姓名", desensitization_service.mask_name(patient_data["patient_name"] or "")),
            ("性别", self._translate_gender(patient.gender)),
            ("年龄", self._calculate_age(patient.birth_date) if patient.birth_date else "未填写"),
        ]
        for key, value in info_pairs:
            lines.append(f"{key}：{value}")
        if patient.medical_history:
            lines.append(f"病史：{patient.medical_history}")
        if patient.allergies:
            lines.append(f"过敏史：{patient.allergies}")
        return "\n".join(lines)

    def _format_medical_history(self, patient: Patient) -> str:
        """格式化病史记录"""
        return patient.medical_history or ""

    def _format_timeline(self, patient: Patient, recent_count: int = 20) -> str:
        """格式化治疗时间线"""
        timeline_list = self._process_timeline_events(patient.timeline_events)
        if not timeline_list:
            return ""
        timeline_list = timeline_list[:recent_count]
        lines = []
        for event in timeline_list:
            line = f"{event['日期']} - {event['类型']}：{event['标题']}"
            if event['描述'] and event['描述'] != '无描述':
                line += f"（{event['描述']}）"
            lines.append(line)
        return "\n".join(lines)

    def _format_pathology(self, patient: Patient) -> str:
        """格式化病理报告（支持多份）"""
        latest_reports = self._extract_latest_reports(patient.pathology_reports)
        if not latest_reports:
            return ""
        lines = []
        for report_type, report_data in latest_reports.items():
            if isinstance(report_data, list):
                # 多份病理报告
                for i, entry in enumerate(report_data):
                    if len(report_data) > 1:
                        lines.append(f"--- 第{i+1}份{report_type} ---")
                    for key, value in entry.items():
                        lines.append(f"{key}：{value}")
            else:
                # 单份报告（兼容旧格式）
                for key, value in report_data.items():
                    lines.append(f"{key}：{value}")
        return "\n".join(lines)

    def _format_lab_by_category(self, patient: Patient, category: str, indicator_count: int = None, recent_count: int = 3) -> str:
        """按分类格式化检验指标（精简格式，无参考范围）"""
        cutoff_date = (get_utc_now() - timedelta(days=self.timeframe_days)).date()

        matching_checks = []
        for check in patient.medical_checks:
            if not check.medical_date or check.medical_date < cutoff_date:
                continue
            has_category = False
            if check.details:
                for detail in check.details:
                    if detail.standard_index and detail.standard_index.category == category:
                        has_category = True
                        break
            if has_category:
                matching_checks.append(check)

        if not matching_checks:
            return ""

        matching_checks.sort(key=lambda c: c.medical_date, reverse=True)
        matching_checks = matching_checks[:recent_count]

        lines = []
        for check in matching_checks:
            date_str = check.medical_date.strftime('%Y-%m-%d')

            category_details = []
            if check.details:
                for detail in check.details:
                    if detail.standard_index and detail.standard_index.category == category:
                        category_details.append(detail)

            # 按 sort 排序，保持指标顺序一致
            category_details.sort(key=lambda d: d.standard_index.sort if d.standard_index and d.standard_index.sort is not None else 0)

            if indicator_count and len(category_details) > indicator_count:
                abnormal = [d for d in category_details if d.index_status == 'abnormal']
                normal = [d for d in category_details if d.index_status != 'abnormal']
                if len(abnormal) >= indicator_count:
                    category_details = abnormal[:indicator_count]
                else:
                    category_details = abnormal + normal[:indicator_count - len(abnormal)]

            all_details = self._extract_all_check_details(category_details)
            for d in all_details:
                mark = "↑" if d['mark'] == "⚠" else ""
                lines.append(f"{date_str} - {d['指标']}：{mark}{d['值']} {d['单位']}")

        return "\n".join(lines)

    def _format_exams(self, patient: Patient, recent_count: int = 2, findings_limit: int = 500) -> str:
        """格式化检查报告"""
        cutoff_date = (get_utc_now() - timedelta(days=self.timeframe_days)).date()

        matching_exams = [
            exam for exam in patient.medical_exams
            if exam.medical_date and exam.medical_date >= cutoff_date
        ]

        if not matching_exams:
            return ""

        matching_exams.sort(key=lambda e: e.medical_date, reverse=True)
        matching_exams = matching_exams[:recent_count]

        lines = []
        for i, exam in enumerate(matching_exams, 1):
            date_str = exam.medical_date.strftime('%Y-%m-%d')
            exam_label = exam.title or (f"{exam.exam_type or '检查'}报告" if exam.exam_type else "检查报告")
            lines.append(f"第{i}次{exam_label}（{date_str}）：")
            if exam.exam_info:
                finding = exam.exam_info
                if len(finding) > findings_limit:
                    finding = finding[:findings_limit] + "..."
                lines.append(f"检查信息：{finding}")
            lines.append(f"诊断结果：{exam.exam_diag or '未填写'}")

        return "\n".join(lines)

    def _format_medical_records(self, patient: Patient, recent_count: int = 30, content_limit: int = 1000) -> str:
        """格式化病情记录（精简格式）"""
        records = self._extract_medical_records(patient.medical_records)
        if not records:
            return ""
        # 只取最近一条，详细展示
        latest = records[0]
        lines = [f"最新病情记录（{latest['日期']}）："]
        lines.append(f"记录名称：{latest['名称']}")
        if latest.get('内容'):
            content = latest['内容']
            if len(content) > content_limit:
                content = content[:content_limit] + "..."
            lines.append(f"病情信息：{content}")
        if latest.get('患者状态'):
            lines.append(f"患者状态：{latest['患者状态']}")

        return "\n".join(lines)

    def _format_medications(self, patient: Patient) -> str:
        """格式化当前用药方案"""
        medications = getattr(patient, "medications", [])
        if not medications:
            return ""

        active_meds = [m for m in medications if m.status == "active"]
        discontinued_meds = [m for m in medications if m.status == "discontinued"]

        lines = []
        if active_meds:
            lines.append("【正在使用】")
            for med in active_meds:
                line = f"- {med.medication_name}"
                if med.dosage:
                    line += f" {med.dosage}"
                if med.frequency:
                    line += f" {med.frequency}"
                if med.route:
                    line += f" ({med.route})"
                if med.start_date:
                    line += f" 起始{med.start_date.strftime('%Y-%m-%d')}"
                lines.append(line)

        if discontinued_meds:
            # 仅展示最近停药的5种
            recent_discontinued = sorted(
                discontinued_meds,
                key=lambda m: m.end_date or datetime.min.date(),
                reverse=True
            )[:5]
            lines.append("【已停药】")
            for med in recent_discontinued:
                line = f"- {med.medication_name}"
                if med.end_date:
                    line += f" 停药{med.end_date.strftime('%Y-%m-%d')}"
                # 停药原因存储在 notes 中
                if med.notes and "停药原因" in med.notes:
                    reason = med.notes.split("停药原因:")[-1].strip().split("\n")[0]
                    line += f"（{reason}）"
                lines.append(line)

        # 副作用信息（如有）
        has_side_effects = any(m.side_effects for m in active_meds)
        if has_side_effects:
            lines.append("【注意事项】")
            for med in active_meds:
                if med.side_effects:
                    lines.append(f"- {med.medication_name}副作用：{med.side_effects}")

        return "\n".join(lines)

    async def _format_summary_or_fallback(
        self,
        patient: Patient,
        db: Optional[AsyncSession],
        summary_type: str,
        fallback_fn,
    ) -> str:
        """读概要优先 + 降级回逐条格式化

        Args:
            patient: 患者对象
            db: 数据库会话（为 None 时直接降级）
            summary_type: 概要类型（treatment/medication_record/status）
            fallback_fn: 降级时的格式化函数
        """
        if not db:
            return fallback_fn()

        from app.services.consultation.summary_service import SummaryService
        svc = SummaryService(db)
        summary_text = await svc.get_summaries_text(
            patient_id=patient.patient_id,
            summary_type=summary_type,
        )
        if summary_text:
            return summary_text

        return fallback_fn()

    # 治疗类事件 category 集合
    TREATMENT_CATEGORIES = {
        "chemotherapy", "radiation", "surgery", "targeted",
        "immunotherapy", "adc", "car_t",
    }

    # 治疗类分类中文映射
    TREATMENT_CATEGORY_MAP = {
        "chemotherapy": "化疗",
        "radiation": "放疗",
        "surgery": "手术",
        "targeted": "靶向治疗",
        "immunotherapy": "免疫治疗",
        "adc": "ADC治疗",
        "car_t": "CAR-T治疗",
    }

    def _format_treatment_records(self, patient: Patient, recent_count: int = 10) -> str:
        """格式化治疗记录（仅治疗类时间线事件）"""
        events = patient.timeline_events
        if not events:
            return ""
        treatment_events = [
            e for e in events
            if e.event_type == "medical" and e.category in self.TREATMENT_CATEGORIES
        ]
        if not treatment_events:
            return ""
        treatment_events.sort(
            key=lambda e: e.event_date if e.event_date else datetime.min.date(),
            reverse=True
        )
        treatment_events = treatment_events[:recent_count]
        lines = []
        for event in treatment_events:
            date_str = event.event_date.strftime("%Y-%m-%d") if event.event_date else "未知"
            cat_label = self.TREATMENT_CATEGORY_MAP.get(event.category, self.CATEGORY_MAP.get(event.category, event.category))
            line = f"{date_str} - {cat_label}：{event.title or '无标题'}"
            if event.description:
                line += f"（{event.description}）"
            lines.append(line)
        return "\n".join(lines)

    def _format_medication_records(self, patient: Patient, recent_count: int = 20) -> str:
        """格式化用药记录（全部用药含完整停药详情）"""
        medications = getattr(patient, "medications", [])
        if not medications:
            return ""
        all_meds = sorted(
            medications,
            key=lambda m: m.start_date or datetime.min.date(),
            reverse=True
        )[:recent_count]
        lines = []
        for med in all_meds:
            status_label = "使用中" if med.status == "active" else "已停药"
            line = f"- {med.medication_name}"
            if med.dosage:
                line += f" {med.dosage}"
            if med.frequency:
                line += f" {med.frequency}"
            if med.route:
                line += f" ({med.route})"
            if med.start_date:
                line += f" 起始{med.start_date.strftime('%Y-%m-%d')}"
            if med.end_date:
                line += f" 结束{med.end_date.strftime('%Y-%m-%d')}"
            line += f" [{status_label}]"
            if med.status != "active" and med.notes and "停药原因" in med.notes:
                reason = med.notes.split("停药原因:")[-1].strip().split("\n")[0]
                line += f"（{reason}）"
            if med.side_effects:
                line += f" 副作用:{med.side_effects}"
            lines.append(line)
        return "\n".join(lines)

    def _format_status_records(self, patient: Patient, recent_count: int = 30, content_limit: int = 500) -> str:
        """格式化状态记录（daily_status 类时间线事件）"""
        events = patient.timeline_events
        if not events:
            return ""
        status_events = [
            e for e in events
            if e.category == "daily_status"
        ]
        if not status_events:
            return ""
        status_events.sort(
            key=lambda e: e.event_date if e.event_date else datetime.min.date(),
            reverse=True
        )
        status_events = status_events[:recent_count]
        lines = []
        for event in status_events:
            date_str = event.event_date.strftime("%Y-%m-%d") if event.event_date else "未知"
            line = f"{date_str}"
            if event.title:
                line += f" {event.title}"
            # 从 life_details JSON 提取状态评分
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
                    memo = details["general_memo"]
                    if len(memo) > content_limit:
                        memo = memo[:content_limit] + "..."
                    line += f" {memo}"
            elif event.description:
                desc = event.description
                if len(desc) > content_limit:
                    desc = desc[:content_limit] + "..."
                line += f" {desc}"
            lines.append(line)
        return "\n".join(lines)

    async def _format_prompt_config_driven(
        self,
        patient: Patient,
        config_items: list,
        user_message: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> str:
        """配置驱动的提示词格式化（精简纯文本格式）"""
        sections = []
        has_diagnostic_requirement = False

        for item in config_items:
            if not item.get("enabled", True):
                continue

            item_type = item["type"]
            content = None

            if item_type == "custom":
                text = item.get("customText", "")
                if text:
                    content = text
            elif item_type == "info":
                content = self._format_basic_info(patient)
            elif item_type == "history":
                content = self._format_medical_history(patient)
            elif item_type == "timeline":
                content = self._format_timeline(
                    patient,
                    recent_count=item.get("recentCount", 20)
                )
            elif item_type == "pathology":
                content = self._format_pathology(patient)
            elif item_type == "lab":
                content = self._format_lab_by_category(
                    patient,
                    category=item.get("category"),
                    indicator_count=item.get("indicatorCount"),
                    recent_count=item.get("recentCount", 3)
                )
            elif item_type == "exam":
                content = self._format_exams(
                    patient,
                    recent_count=item.get("recentCount", 2),
                    findings_limit=item.get("findingsLimit", 500)
                )
            elif item_type == "record":
                content = self._format_medical_records(
                    patient,
                    recent_count=item.get("recentCount", 30),
                    content_limit=item.get("contentLimit", 1000)
                )
            elif item_type == "medication":
                content = self._format_medications(patient)
            elif item_type == "treatment":
                content = await self._format_summary_or_fallback(
                    patient, db, "treatment",
                    fallback_fn=lambda: self._format_treatment_records(
                        patient, recent_count=item.get("recentCount", 10)
                    ),
                )
            elif item_type == "medication_record":
                content = await self._format_summary_or_fallback(
                    patient, db, "medication_record",
                    fallback_fn=lambda: self._format_medication_records(
                        patient, recent_count=item.get("recentCount", 20)
                    ),
                )
            elif item_type == "status":
                content = await self._format_summary_or_fallback(
                    patient, db, "status",
                    fallback_fn=lambda: self._format_status_records(
                        patient,
                        recent_count=item.get("recentCount", 30),
                        content_limit=item.get("contentLimit", 500),
                    ),
                )

            if content:
                # lab 类型使用 "血常规记录：" 格式的标题
                if item_type == "lab":
                    category_cn = self.CATEGORY_MAP.get(item.get("category", ""), item.get("name", ""))
                    sections.append(f"{category_cn}记录：")
                else:
                    sections.append(f"{item['name']}：")
                sections.append(content)
                sections.append("")

                if item_type == "custom" and "诊断" in item.get("name", ""):
                    has_diagnostic_requirement = True

        if user_message:
            sections.append("患者/医生补充说明：")
            sections.append(user_message)
            sections.append("")

        if not has_diagnostic_requirement:
            sections.append("请基于以上患者资料，提供专业的会诊意见。")

        return "\n".join(sections)

    def _extract_medical_records(self, records: list) -> list:
        """提取病情记录

        Args:
            records: MedicalRecord 列表

        Returns:
            格式化的病情记录列表
        """
        if not records:
            return []

        # 按日期降序排序，限制最近 30 条
        sorted_records = sorted(
            records,
            key=lambda r: r.record_date if r.record_date else datetime.min.date(),
            reverse=True
        )[:30]

        result = []
        for record in sorted_records:
            item = {
                "日期": record.record_date.strftime("%Y-%m-%d") if record.record_date else "未知",
                "名称": record.record_name or "未填写",
                "类型": record.record_type or "未填写",
            }
            if record.patient_status:
                item["患者状态"] = record.patient_status
            if record.record_info:
                item["内容"] = record.record_info
            if record.record_drug:
                item["用药记录"] = record.record_drug
            if record.hospital:
                item["医院"] = record.hospital
            result.append(item)

        return result

    def _extract_abnormal_details(self, details: list) -> list:
        """提取异常检验指标明细（仅异常）— 兼容旧调用"""
        if not details:
            return []
        results = []
        for detail in details:
            if detail.index_status != 'abnormal':
                continue
            index_name = detail.index_name or ""
            if detail.standard_index:
                index_name = detail.standard_index.index_name or index_name
            item = {
                "指标": index_name or f"指标{detail.medical_detail_id}",
                "结果": f"{detail.index_value or ''}{detail.index_unit or ''}",
            }
            if detail.reference_value:
                item["参考范围"] = detail.reference_value
            results.append(item)
        return results

    def _extract_all_check_details(self, details: list) -> list:
        """提取全部检验指标明细（正常 + 异常）

        Args:
            details: MedicalCheckDetail 列表

        Returns:
            全部指标列表，异常指标前缀⚠，正常指标前缀两空格
        """
        if not details:
            return []

        result = []
        for detail in details:
            is_abnormal = detail.index_status == 'abnormal'
            mark = "⚠" if is_abnormal else "  "

            # 优先使用标准指标名称
            index_name = detail.index_name or ""
            category_cn = "其他"
            if detail.standard_index:
                index_name = detail.standard_index.index_name or index_name
                if detail.standard_index.category:
                    category_cn = self.CATEGORY_MAP.get(detail.standard_index.category, detail.standard_index.category)

            value = detail.index_value or ""
            unit = detail.index_unit or ""
            ref = detail.reference_value or ""

            item = {
                "mark": mark,
                "指标": index_name or f"指标{detail.medical_detail_id}",
                "值": value,
                "单位": unit,
                "参考": ref,
                "category": category_cn,
            }
            result.append(item)

        return result

    def _process_timeline_events(self, events: list) -> list:
        """处理时间线事件

        Args:
            events: 时间线事件列表

        Returns:
            格式化的事件列表
        """
        # 按日期降序排序并限制数量
        sorted_events = sorted(
            events,
            key=lambda e: e.event_date if e.event_date else datetime.min.date(),
            reverse=True
        )[:20]

        timeline_list = []
        for event in sorted_events:
            timeline_list.append({
                "日期": event.event_date.strftime("%Y-%m-%d") if event.event_date else "未知",
                "类型": event.event_type or "未知",
                "标题": event.title or "无标题",
                "描述": event.description or "无描述",
            })

        return timeline_list

    def _format_ihc_for_prompt(self, pathology) -> str:
        """格式化免疫组化数据，优先使用结构化 IHC 标记物"""
        ihc_markers = getattr(pathology, 'ihc_markers', None)
        if ihc_markers:
            parts = []
            for m in ihc_markers:
                s = m.marker_name
                if m.result:
                    s += f": {m.result}"
                if m.intensity:
                    s += f"({m.intensity})"
                if m.percentage:
                    s += f" {m.percentage}"
                parts.append(s)
            return ', '.join(parts)
        return getattr(pathology, "immunohistochemistry", None) or "未填写"

    def _format_gene_testing_for_prompt(self, pathology) -> str:
        """格式化基因检测数据，解析 JSON 结构展示摘要"""
        import json
        gene_testing = getattr(pathology, "gene_testing", None)
        if not gene_testing:
            return "未填写"
        # 尝试解析 JSON 结构
        try:
            data = json.loads(gene_testing)
            if isinstance(data, dict):
                test_items = data.get('test_items', [])
                test_method = data.get('test_method')
                parts = []
                for item in test_items:
                    gene = item.get('gene', '')
                    result = item.get('result', '')
                    if gene and result:
                        parts.append(f"{gene}: {result}")
                    elif gene:
                        parts.append(gene)
                summary = '; '.join(parts)
                if test_method:
                    summary += f" ({test_method})"
                return summary if summary else "未填写"
            # 非预期结构，按纯文本处理
            return str(data) if data else "未填写"
        except (json.JSONDecodeError, TypeError):
            # 纯文本向后兼容
            return gene_testing if gene_testing else "未填写"

    def _extract_latest_reports(self, pathology_reports: list) -> dict:
        """提取所有病理报告

        Args:
            pathology_reports: 病理报告列表

        Returns:
            报告字典，"病理报告" 键下为列表（按日期倒序）
        """
        reports = {}

        # 获取所有病理报告（按日期倒序）
        if pathology_reports:
            sorted_reports = sorted(
                pathology_reports,
                key=lambda r: r.report_date if r.report_date else datetime.min.date(),
                reverse=True
            )

            pathology_list = []
            for i, pathology in enumerate(sorted_reports):
                entry = {}
                if pathology.report_title:
                    entry["标题"] = pathology.report_title
                entry["日期"] = pathology.report_date.strftime("%Y-%m-%d") if pathology.report_date else "未知"
                entry["诊断"] = getattr(pathology, "diagnosis", None) or "未填写"
                entry["类型"] = getattr(pathology, "cancer_type", None) or "未填写"
                entry["分期"] = getattr(pathology, "stage", None) or "未填写"
                entry["组织学类型"] = getattr(pathology, "histology_type", None) or "未填写"
                entry["免疫组化"] = self._format_ihc_for_prompt(pathology)
                entry["基因检测"] = self._format_gene_testing_for_prompt(pathology)
                pathology_list.append(entry)

            reports["病理报告"] = pathology_list

        return reports

    def _extract_recent_reports(
        self,
        medical_checks: list,
        medical_exams: list,
        days: int
    ) -> dict:
        """提取近期报告

        Args:
            medical_checks: 检验报告列表
            medical_exams: 检查报告列表
            days: 时间范围（天）

        Returns:
            近期报告字典
        """
        # 注意：medical_date 字段是 date 类型，所以 cutoff_date 也需要转换为 date
        cutoff_date = (get_utc_now() - timedelta(days=days)).date()

        reports = {
            "检验报告": [],
            "检查报告": []
        }

        # 处理检验报告
        for check in medical_checks:
            if check.medical_date and check.medical_date >= cutoff_date:
                check_info = {
                    "日期": check.medical_date.strftime("%Y-%m-%d"),
                    "医院": check.hospital or "未填写",
                    "类型": self._get_check_categories(check.details) or "综合检验",
                    "指标数": len(check.details) if check.details else 0,
                }
                # 提取全部指标明细（正常+异常）
                all_details = self._extract_all_check_details(check.details)
                if all_details:
                    check_info["全部指标"] = all_details
                reports["检验报告"].append(check_info)

        # 处理检查报告
        for exam in medical_exams:
            if exam.medical_date and exam.medical_date >= cutoff_date:
                exam_info = {
                    "日期": exam.medical_date.strftime("%Y-%m-%d"),
                    "医院": exam.hospital or "未填写",
                    "类型": exam.exam_type or "未填写",
                    "结论": exam.exam_diag or "未填写",
                }
                # 影像所见/检查描述
                if exam.exam_info:
                    exam_info["影像所见"] = exam.exam_info
                reports["检查报告"].append(exam_info)

        return reports

    # ========== 辅助方法 ==========

    def _get_check_categories(self, details) -> str:
        """从检验明细中提取分类信息

        通过 standard_index 关联获取 category，去重后拼接
        """
        if not details:
            return ""

        categories = set()
        for detail in details:
            if detail.standard_index and detail.standard_index.category:
                cat = detail.standard_index.category
                categories.add(self.CATEGORY_MAP.get(cat, cat))

        return "/".join(sorted(categories)) if categories else ""

    def _calculate_age(self, birth_date) -> str:
        """计算年龄

        Args:
            birth_date: 出生日期

        Returns:
            年龄字符串
        """
        if not birth_date:
            return "未知"

        today = datetime.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return f"{age}岁"

    @staticmethod
    def _translate_gender(gender: str | None) -> str:
        """将性别字段翻译为中文"""
        mapping = {"male": "男", "female": "女", "unknown": "未知"}
        if not gender:
            return "未填写"
        return mapping.get(gender, gender)
