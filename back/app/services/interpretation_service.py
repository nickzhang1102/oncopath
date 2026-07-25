"""AI 检验报告解读服务

使用 LLM 将专业检验指标翻译成通俗语言，包含：
- 整体评估
- 异常指标解读
- 趋势变化
- 建议与提醒
"""
import logging
import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any

import httpx
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.medical import MedicalCheck, MedicalCheckDetail, MedicalIndex, MedicalExam, PathologyReport
from app.models.patient import Patient
from app.utils.time_utils import calculate_age, get_utc_now, utc_isoformat

logger = logging.getLogger(__name__)

# 提取复查建议的正则
FOLLOW_UP_PATTERN = re.compile(
    r"建议(\d+)(天|周|月|年)后复查(.+?)(?:[，。,.\n]|$)"
)

SYSTEM_PROMPT = """你是一位拥有 20 年临床检验经验的检验科专家，正在为患者解读检验报告。请用通俗易懂的语言完成以下解读。

请按以下结构输出（使用 Markdown 格式）：

## 整体评估
（2-3句话概括本次检查的总体情况）

## 异常指标解读
（对每个异常指标，说明可能原因和需要关注什么）

## 趋势变化
（与历史对比的显著变化，如无历史数据则说明"无历史数据对比"）

## 建议与提醒
（饮食/生活/复查建议，如有复查需要请明确写"建议X周后复查XXX"）

注意：
- 使用通俗语言，避免专业术语或给出解释
- 不要做诊断，只做解读
- 必须在结尾附上免责声明
- 如果建议复查，格式为"建议{N}{单位}后复查{项目}"
"""

EXAM_SYSTEM_PROMPT = """你是一位拥有 20 年临床影像学经验的影像科专家，正在为患者解读影像检查报告。请用通俗易懂的语言完成以下解读。

请按以下结构输出（使用 Markdown 格式）：

## 整体评估
（2-3句话概括本次检查的总体情况，说明检查类型和主要发现）

## 关键发现解读
（对检查所见的异常发现进行通俗解释，说明可能的临床意义）

## 趋势变化
（与历史同类检查对比的显著变化，如病灶变化、新发现象或好转，如无历史数据则说明"无历史数据对比"）

## 诊断意见说明
（对医生的诊断意见进行解读，帮助患者理解）

## 建议与提醒
（复查/随诊建议，如有复查需要请明确写"建议X周后复查XXX"）

注意：
- 使用通俗语言，避免专业术语或给出解释
- 不要做诊断，只做解读
- 必须在结尾附上免责声明
- 如果建议复查，格式为"建议{N}{单位}后复查{项目}"
"""

PATHOLOGY_SYSTEM_PROMPT = """你是一位拥有 20 年病理学经验的病理科专家，正在为患者解读病理报告。请用通俗易懂的语言完成以下解读。

请按以下结构输出（使用 Markdown 格式）：

## 整体评估
（2-3句话概括病理报告的总体情况，说明诊断结论类型和严重程度）

## 诊断结论解读
（对病理诊断进行通俗解释，包括病变性质、组织学类型等）

## 趋势变化
（与既往病理报告的对比分析，包括诊断结论变化、分期变化、免疫组化结果变化等，如无历史数据则说明"无历史数据对比"）

## 免疫组化/基因检测说明
（对免疫组化结果和基因检测结果进行解读，说明其临床意义）

## 建议与提醒
（治疗/复查建议，如有复查需要请明确写"建议X周后复查XXX"）

注意：
- 使用通俗语言，避免专业术语或给出解释
- 不要做诊断，只做解读
- 必须在结尾附上免责声明
- 如果建议复查，格式为"建议{N}{单位}后复查{项目}"
"""

DISCLAIMER = "\n\n---\n\n⚠️ 以上解读仅供参考，不构成医疗诊断建议。如有疑问请咨询您的主治医生。"

_GENDER_MAP = {"male": "男", "female": "女", "unknown": "未知"}


class InterpretationService:
    """AI 检验报告解读服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client: Optional[AsyncOpenAI] = None
        self.model = settings.interpretation_model_name
        self.timeout = settings.interpretation_timeout
        self._initialized = False

    def _initialize(self):
        """延迟初始化解读专用 LLM 客户端"""
        if self._initialized:
            return
        try:
            api_key = settings.interpretation_api_key
            if api_key:
                timeout_config = httpx.Timeout(
                    connect=10.0,
                    read=float(self.timeout),
                    write=30.0,
                    pool=10.0,
                )
                client_kwargs: Dict = {
                    "api_key": api_key,
                    "timeout": timeout_config,
                }
                api_base = settings.interpretation_api_base
                if api_base:
                    client_kwargs["base_url"] = api_base
                self.client = AsyncOpenAI(**client_kwargs)
                logger.info(
                    f"解读LLM初始化成功, model={self.model}, "
                    f"base_url={api_base}"
                )
            else:
                logger.warning("未配置解读LLM API_KEY, 解读服务将不可用")
            self._initialized = True
        except Exception as e:
            logger.error(f"解读LLM初始化失败: {e}")

    async def _llm_analyze(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """调用解读专用 LLM"""
        self._initialize()
        if not self.client:
            raise RuntimeError("解读LLM服务未初始化")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=messages,
            stream=False,
        )

        if response.choices and response.choices[0].message.content:
            tokens_used = (
                response.usage.total_tokens
                if hasattr(response, "usage") and response.usage
                else 0
            )
            return {
                "content": response.choices[0].message.content,
                "tokens_used": tokens_used,
            }
        else:
            raise RuntimeError("解读LLM返回空响应")

    async def _execute_interpretation(
        self,
        user_message: str,
        system_prompt: str,
        save_target: Any,
        user_id: int,
        max_tokens: int = 16384,
    ) -> Dict[str, Any]:
        """通用解读执行流程：LLM调用 → 保存 → 提取复查建议"""
        result = await self._llm_analyze(
            system_prompt=system_prompt,
            user_prompt=user_message,
            max_tokens=max_tokens
        )

        interpretation = result["content"] + DISCLAIMER

        # 保存解读结果
        save_target.interpretation = interpretation
        save_target.interpretation_at = get_utc_now()
        await self.db.flush()

        # 提取复查建议
        follow_ups = self._extract_follow_ups(interpretation, getattr(save_target, 'medical_date', None) or getattr(save_target, 'report_date', None) or getattr(save_target, 'medical_date', None))
        await self._create_follow_up_reminders(
            patient_id=save_target.patient_id,
            user_id=user_id,
            follow_ups=follow_ups,
            source_id=getattr(save_target, 'exam_id', None) or getattr(save_target, 'report_id', None) or getattr(save_target, 'medical_id', None),
        )

        return {
            "interpretation": interpretation,
            "interpretation_at": utc_isoformat(save_target.interpretation_at),
            "follow_ups": follow_ups,
        }

    async def interpret_check(
        self, check_id: int, user_id: int
    ) -> Dict[str, Any]:
        """生成检验报告 AI 解读

        Returns:
            dict: {interpretation, follow_ups}
        """
        # 1. 查询检验报告 + 指标详情
        check, details, patient = await self._load_check_data(check_id)
        if not check:
            raise ValueError("检验报告不存在")

        # 2. 查询历史趋势（同类型检查）
        history_data = await self._load_history_trend(
            check.patient_id, check.medical_date, details, check.category
        )

        # 3. 构建 prompt
        user_message = self._build_user_message(
            check, details, patient, history_data
        )

        # 4. 执行解读（LLM → 保存 → 提取复查建议）
        return await self._execute_interpretation(
            user_message=user_message,
            system_prompt=SYSTEM_PROMPT,
            save_target=check,
            user_id=user_id,
        )

    async def get_interpretation(self, check_id: int) -> Optional[Dict[str, Any]]:
        """获取已有解读"""
        result = await self.db.execute(
            select(MedicalCheck).where(
                MedicalCheck.medical_id == check_id
            )
        )
        check = result.scalar_one_or_none()
        if not check or not check.interpretation:
            return None

        return {
            "interpretation": check.interpretation,
            "interpretation_at": utc_isoformat(check.interpretation_at)
            if check.interpretation_at
            else None,
        }

    # ===== 检查报告解读 =====

    async def _load_exam_history(
        self,
        patient_id: int,
        current_date: date,
        exam_type: Optional[str] = None,
    ) -> List[Dict]:
        """加载同类型检查的历史报告"""
        conditions = [
            MedicalExam.patient_id == patient_id,
            MedicalExam.medical_date < current_date,
        ]
        if exam_type:
            conditions.append(MedicalExam.exam_type == exam_type)

        result = await self.db.execute(
            select(MedicalExam)
            .where(*conditions)
            .order_by(MedicalExam.medical_date.desc())
            .limit(10)
        )
        history_exams = result.scalars().all()

        return [{
            "date": e.medical_date.isoformat() if e.medical_date else None,
            "title": e.title,
            "exam_type": e.exam_type,
            "exam_info": e.exam_info,
            "exam_diag": e.exam_diag,
        } for e in history_exams]

    async def interpret_exam(
        self, exam_id: int, user_id: int
    ) -> Dict[str, Any]:
        """生成检查报告 AI 解读"""
        # 1. 查询检查报告 + 患者信息
        result = await self.db.execute(
            select(MedicalExam)
            .where(MedicalExam.exam_id == exam_id)
        )
        exam = result.scalar_one_or_none()
        if not exam:
            raise ValueError("检查报告不存在")

        patient_result = await self.db.execute(
            select(Patient).where(Patient.patient_id == exam.patient_id)
        )
        patient = patient_result.scalar_one_or_none()

        # 2. 查询同类型历史检查报告
        history_data = await self._load_exam_history(
            exam.patient_id, exam.medical_date, exam.exam_type
        )

        # 3. 构建 prompt
        parts = []
        if patient:
            parts.append(f"患者信息：{_GENDER_MAP.get(patient.gender, '未知')}性，年龄{calculate_age(patient.birth_date) or '未知'}岁")
        if exam.medical_date:
            parts.append(f"检查日期：{exam.medical_date.isoformat()}")
        if exam.hospital:
            parts.append(f"检查医院：{exam.hospital}")
        if exam.title:
            parts.append(f"报告标题：{exam.title}")
        if exam.exam_type:
            parts.append(f"检查类型：{exam.exam_type}")
        if exam.exam_info:
            parts.append(f"\n检查所见：\n{exam.exam_info}")
        if exam.exam_diag:
            parts.append(f"\n诊断意见：\n{exam.exam_diag}")
        if exam.comment:
            parts.append(f"\n备注：{exam.comment}")

        # 历史数据
        if history_data:
            parts.append("\n历史同类检查记录：")
            for h in history_data[:5]:
                parts.append(f"- {h['date']} {h['exam_type'] or '检查'}")
                if h.get('exam_diag'):
                    parts.append(f"  诊断意见：{h['exam_diag'][:200]}")
                if h.get('exam_info'):
                    parts.append(f"  检查所见：{h['exam_info'][:200]}")

        user_message = "\n".join(parts)

        # 4. 执行解读
        return await self._execute_interpretation(
            user_message=user_message,
            system_prompt=EXAM_SYSTEM_PROMPT,
            save_target=exam,
            user_id=user_id,
        )

    async def get_exam_interpretation(self, exam_id: int) -> Optional[Dict[str, Any]]:
        """获取检查报告已有解读"""
        result = await self.db.execute(
            select(MedicalExam).where(MedicalExam.exam_id == exam_id)
        )
        exam = result.scalar_one_or_none()
        if not exam or not exam.interpretation:
            return None

        return {
            "interpretation": exam.interpretation,
            "interpretation_at": utc_isoformat(exam.interpretation_at)
            if exam.interpretation_at
            else None,
        }

    # ===== 病理报告解读 =====

    async def _load_pathology_history(
        self,
        patient_id: int,
        current_date: date,
    ) -> List[Dict]:
        """加载历史病理报告"""
        result = await self.db.execute(
            select(PathologyReport)
            .options(selectinload(PathologyReport.ihc_markers))
            .where(
                PathologyReport.patient_id == patient_id,
                PathologyReport.report_date < current_date,
            )
            .order_by(PathologyReport.report_date.desc())
            .limit(10)
        )
        history_reports = result.scalars().all()

        return [{
            "date": r.report_date.isoformat() if r.report_date else None,
            "diagnosis": r.diagnosis,
            "cancer_type": r.cancer_type,
            "stage": r.stage,
            "histology_type": r.histology_type,
            "immunohistochemistry": r.immunohistochemistry,
            "ihc_markers": [{
                "marker_name": m.marker_name,
                "result": m.result,
                "intensity": m.intensity,
                "percentage": m.percentage,
            } for m in (r.ihc_markers or [])],
            "gene_testing": r.gene_testing,
        } for r in history_reports]

    async def interpret_pathology(
        self, report_id: int, user_id: int
    ) -> Dict[str, Any]:
        """生成病理报告 AI 解读"""
        # 1. 查询病理报告 + 患者信息
        result = await self.db.execute(
            select(PathologyReport)
            .options(selectinload(PathologyReport.ihc_markers))
            .where(PathologyReport.report_id == report_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            raise ValueError("病理报告不存在")

        patient_result = await self.db.execute(
            select(Patient).where(Patient.patient_id == report.patient_id)
        )
        patient = patient_result.scalar_one_or_none()

        # 2. 查询历史病理报告
        history_data = await self._load_pathology_history(
            report.patient_id, report.report_date
        )

        # 3. 构建 prompt
        parts = []
        if patient:
            parts.append(f"患者信息：{_GENDER_MAP.get(patient.gender, '未知')}性，年龄{calculate_age(patient.birth_date) or '未知'}岁")
        if report.report_date:
            parts.append(f"报告日期：{report.report_date.isoformat()}")
        if report.hospital:
            parts.append(f"医院：{report.hospital}")
        if report.report_title:
            parts.append(f"报告标题：{report.report_title}")
        if report.diagnosis:
            parts.append(f"\n病理诊断：{report.diagnosis}")
        if report.cancer_type:
            parts.append(f"癌种/肿瘤类型：{report.cancer_type}")
        if report.stage:
            parts.append(f"临床分期：{report.stage}")
        if report.histology_type:
            parts.append(f"组织学类型：{report.histology_type}")
        if report.immunohistochemistry:
            parts.append(f"\n免疫组化结果：\n{report.immunohistochemistry}")
        if report.ihc_markers:
            ihc_lines = []
            for m in report.ihc_markers:
                parts_list = [f"{m.marker_name}"]
                if m.result:
                    parts_list.append(m.result)
                if m.intensity:
                    parts_list.append(f"({m.intensity})")
                if m.percentage:
                    parts_list.append(f"阳性{m.percentage}")
                ihc_lines.append("  - " + " ".join(parts_list))
            if ihc_lines:
                parts.append("\n结构化免疫组化：\n" + "\n".join(ihc_lines))
        if report.gene_testing:
            parts.append(f"\n基因检测：\n{report.gene_testing}")
        if report.comment:
            parts.append(f"\n备注：{report.comment}")

        # 历史数据
        if history_data:
            parts.append("\n历史病理报告：")
            for h in history_data[:5]:
                parts.append(f"- {h['date']}")
                if h.get('diagnosis'):
                    parts.append(f"  病理诊断：{h['diagnosis'][:200]}")
                if h.get('stage'):
                    parts.append(f"  分期：{h['stage']}")
                if h.get('ihc_markers'):
                    ihc_summary = "; ".join([f"{m['marker_name']}({m['result'] or '-'})" for m in h['ihc_markers'] if m.get('marker_name')])
                    if ihc_summary:
                        parts.append(f"  免疫组化：{ihc_summary[:200]}")
                if h.get('gene_testing'):
                    parts.append(f"  基因检测：{h['gene_testing'][:200]}")

        user_message = "\n".join(parts)

        # 4. 执行解读
        return await self._execute_interpretation(
            user_message=user_message,
            system_prompt=PATHOLOGY_SYSTEM_PROMPT,
            save_target=report,
            user_id=user_id,
        )

    async def get_pathology_interpretation(self, report_id: int) -> Optional[Dict[str, Any]]:
        """获取病理报告已有解读"""
        result = await self.db.execute(
            select(PathologyReport).where(PathologyReport.report_id == report_id)
        )
        report = result.scalar_one_or_none()
        if not report or not report.interpretation:
            return None

        return {
            "interpretation": report.interpretation,
            "interpretation_at": utc_isoformat(report.interpretation_at)
            if report.interpretation_at
            else None,
        }

    # ===== 已有方法（不变） =====

    async def _load_check_data(
        self, check_id: int
    ) -> tuple:
        """加载检验报告、指标详情和患者信息"""
        result = await self.db.execute(
            select(MedicalCheck)
            .options(selectinload(MedicalCheck.details))
            .where(MedicalCheck.medical_id == check_id)
        )
        check = result.scalar_one_or_none()
        if not check:
            return None, [], None

        # 查询患者
        patient_result = await self.db.execute(
            select(Patient).where(Patient.patient_id == check.patient_id)
        )
        patient = patient_result.scalar_one_or_none()

        return check, check.details, patient

    async def _load_history_trend(
        self,
        patient_id: int,
        current_date: date,
        current_details: List[MedicalCheckDetail],
        category: Optional[str] = None,
    ) -> List[Dict]:
        """加载同类型检查的历史趋势数据"""
        if not current_details:
            return []

        # 取当前异常指标的 index_id
        abnormal_index_ids = [
            d.index_id
            for d in current_details
            if d.index_id and d.index_status in ("high", "low", "abnormal")
        ]
        if not abnormal_index_ids:
            return []

        # 查询历史同类型检查（最多20次），按分类过滤以获取精准的同类历史
        conditions = [
            MedicalCheck.patient_id == patient_id,
            MedicalCheck.medical_date < current_date,
        ]
        if category:
            conditions.append(MedicalCheck.category == category)

        history_result = await self.db.execute(
            select(MedicalCheck)
            .options(selectinload(MedicalCheck.details))
            .where(*conditions)
            .order_by(MedicalCheck.medical_date.desc())
            .limit(20)
        )
        history_checks = history_result.scalars().all()

        trends = []
        for check in history_checks:
            for detail in check.details:
                if detail.index_id in abnormal_index_ids:
                    trends.append({
                        "date": check.medical_date.isoformat(),
                        "index_name": detail.index_name,
                        "value": detail.index_value,
                        "unit": detail.index_unit,
                        "status": detail.index_status,
                    })

        return trends

    def _build_user_message(
        self,
        check: MedicalCheck,
        details: List[MedicalCheckDetail],
        patient: Optional[Patient],
        history_data: List[Dict],
    ) -> str:
        """构建 LLM 用户消息"""
        parts = []

        # 患者信息（脱敏）
        if patient:
            parts.append(f"患者信息：{_GENDER_MAP.get(patient.gender, '未知')}性，年龄{calculate_age(patient.birth_date) or '未知'}岁")
        parts.append(f"检查日期：{check.medical_date.isoformat()}")
        if check.hospital:
            parts.append(f"检查医院：{check.hospital}")

        # 异常指标
        abnormal = [
            d for d in details if d.index_status in ("high", "low", "abnormal")
        ]
        if abnormal:
            parts.append("\n异常指标：")
            for d in abnormal:
                status_label = {"high": "偏高", "low": "偏低", "abnormal": "异常"}.get(
                    d.index_status, d.index_status
                )
                parts.append(
                    f"- {d.index_name}: {d.index_value} {d.index_unit or ''} "
                    f"（{status_label}，参考范围: {d.reference_value or '无'}）"
                )
        else:
            parts.append("\n所有指标均在正常范围内。")

        # 正常指标摘要
        normal = [d for d in details if d.index_status not in ("high", "low", "abnormal")]
        if normal:
            parts.append(f"\n正常指标（共{len(normal)}项）：")
            for d in normal[:10]:  # 最多展示10项
                parts.append(
                    f"- {d.index_name}: {d.index_value} {d.index_unit or ''}"
                )
            if len(normal) > 10:
                parts.append(f"- ...等{len(normal)}项")

        # 历史趋势
        if history_data:
            parts.append("\n历史趋势：")
            for h in history_data[:15]:
                status_label = {"high": "偏高", "low": "偏低", "abnormal": "异常"}.get(
                    h["status"], ""
                )
                parts.append(
                    f"- {h['date']} {h['index_name']}: {h['value']} {h['unit']} {status_label}"
                )

        return "\n".join(parts)

    def _extract_follow_ups(
        self, interpretation: str, source_date_holder: Any
    ) -> List[Dict[str, Any]]:
        """从解读文本中提取复查建议"""
        follow_ups = []
        # 获取日期：支持 MedicalCheck/MedicalExam/PathologyReport/普通date对象
        if hasattr(source_date_holder, 'medical_date'):
            source_date = source_date_holder.medical_date
        elif hasattr(source_date_holder, 'report_date'):
            source_date = source_date_holder.report_date
        elif isinstance(source_date_holder, date):
            source_date = source_date_holder
        else:
            source_date = None

        if not source_date:
            return follow_ups

        for match in FOLLOW_UP_PATTERN.finditer(interpretation):
            num, unit, item = match.group(1), match.group(2), match.group(3).strip()
            # 计算提醒日期
            from dateutil.relativedelta import relativedelta

            delta_map = {
                "天": lambda n: relativedelta(days=int(n)),
                "周": lambda n: relativedelta(weeks=int(n)),
                "月": lambda n: relativedelta(months=int(n)),
                "年": lambda n: relativedelta(years=int(n)),
            }
            delta_func = delta_map.get(unit)
            if delta_func:
                reminder_date = source_date + delta_func(num)
                follow_ups.append({
                    "title": f"复查{item}",
                    "description": f"建议{num}{unit}后复查{item}",
                    "reminder_date": reminder_date.isoformat(),
                    "source_type": "interpretation",
                })

        return follow_ups

    async def _create_follow_up_reminders(
        self,
        check: Any = None,
        follow_ups: List[Dict] = None,
        user_id: int = None,
        patient_id: int = None,
        source_id: int = None,
    ):
        """从提取的复查建议自动创建随访提醒"""
        if not follow_ups:
            return

        # 兼容旧接口：从check对象获取patient_id
        if check is not None:
            if hasattr(check, 'patient_id'):
                patient_id = check.patient_id
            if hasattr(check, 'medical_id'):
                source_id = check.medical_id
            elif hasattr(check, 'exam_id'):
                source_id = check.exam_id
            elif hasattr(check, 'report_id'):
                source_id = check.report_id

        if not patient_id or not user_id:
            return

        from app.models.follow_up import FollowUpReminder
        from datetime import date as date_type

        for fu in follow_ups:
            reminder = FollowUpReminder(
                patient_id=patient_id,
                account_id=user_id,
                title=fu["title"],
                description=fu["description"],
                reminder_date=date_type.fromisoformat(fu["reminder_date"]),
                source_type="interpretation",
                source_id=source_id,
            )
            self.db.add(reminder)

        await self.db.flush()
        logger.info(f"已创建 {len(follow_ups)} 条随访提醒")