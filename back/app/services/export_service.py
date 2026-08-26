"""数据导出服务

支持 PDF 导出：检验报告 / 检查报告 / 病理报告 / 指标趋势 / 时间线 / 完整病历
使用 Playwright (Chromium) 生成 PDF，原生支持中文

注意：使用 sync_playwright + asyncio.to_thread() 而非 async_playwright，
因为 Windows 上 uvicorn 的事件循环对 asyncio.create_subprocess_exec 支持
不完整，会导致 NotImplementedError。
"""
import asyncio
import logging
import re
import threading
import markdown as md
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, BaseLoader, FileSystemLoader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.medical import MedicalCheck, MedicalCheckDetail, MedicalExam, PathologyReport
from app.models.patient import Patient
from app.models.medication import Medication
from app.utils.time_utils import calculate_age
from app.services.timeline_aggregator import CATEGORY_LABELS

logger = logging.getLogger(__name__)


# ===== Playwright 浏览器实例管理（同步 API + 线程安全） =====
_pw_lock = threading.Lock()
_pw = None       # sync_playwright 实例
_browser = None  # 同步 Browser 单例
# 限制并发页面数，防止线程池耗尽和内存溢出
_page_semaphore = threading.Semaphore(5)

# PDF 渲染超时（毫秒）
_PAGE_CONTENT_TIMEOUT = 30_000


def _get_or_create_browser():
    """获取或创建 Playwright 同步 Browser 单例（线程安全，在调用线程中执行）"""
    global _pw, _browser
    with _pw_lock:
        if _browser and _browser.is_connected():
            return _browser
        # Browser 已断开，清理后重建
        if _browser:
            logger.warning("Playwright Browser 已断开，正在重建")
            _browser = None
        if _pw is None:
            from playwright.sync_api import sync_playwright
            _pw = sync_playwright().start()
        _browser = _pw.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-gpu', '--font-render-hinting=none'],
        )
        logger.info("Playwright Browser 已启动: %s", _browser.version)
        return _browser


def _sync_html_to_pdf(html: str) -> bytes:
    """同步方式：使用 Playwright 将 HTML 转为 PDF（在线程池中调用）"""
    _page_semaphore.acquire()
    try:
        browser = _get_or_create_browser()
        page = browser.new_page()
        try:
            page.set_content(html, wait_until="networkidle", timeout=_PAGE_CONTENT_TIMEOUT)
            pdf_bytes = page.pdf(
                format="A4",
                margin={"top": "2cm", "bottom": "2cm", "left": "2cm", "right": "2cm"},
                print_background=True,
            )
            return pdf_bytes
        finally:
            try:
                page.close()
            except Exception:
                pass
    finally:
        _page_semaphore.release()


def close_playwright_browser():
    """关闭 Playwright Browser 实例（应用关闭时调用）"""
    global _pw, _browser
    with _pw_lock:
        if _browser:
            try:
                _browser.close()
            except Exception as e:
                logger.warning("关闭 Browser 失败: %s", e)
            _browser = None
        if _pw:
            try:
                _pw.stop()
            except Exception as e:
                logger.warning("停止 Playwright 失败: %s", e)
            _pw = None


# 危险标签黑名单：可执行代码/外部资源/表单/样式/命名空间攻击
_DANGEROUS_TAGS = (
    'script', 'iframe', 'object', 'embed', 'form', 'input',
    'textarea', 'button', 'svg', 'math', 'style', 'link', 'meta',
    'base', 'applet', 'frame', 'frameset', 'noscript',
)

# 危险标签匹配正则（预编译）
_DANGEROUS_TAG_RE = re.compile(
    r'<\s*/?\s*(?:' + '|'.join(_DANGEROUS_TAGS) + r')[^>]*>',
    re.IGNORECASE,
)
_EVENT_HANDLER_RE = re.compile(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', re.IGNORECASE)
_JS_PROTO_RE = re.compile(r'href\s*=\s*["\']javascript:', re.IGNORECASE)


def _sanitize_html(text: str) -> str:
    """过滤 HTML 中的危险标签，保留安全标签用于 PDF 渲染"""
    if not text:
        return text
    text = _DANGEROUS_TAG_RE.sub('', text)
    text = _EVENT_HANDLER_RE.sub('', text)
    text = _JS_PROTO_RE.sub('href="', text)
    return text


# Jinja2 环境（autoescape 开启防止 XSS，从模板目录加载）
_TEMPLATE_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
)

# PDF 页面样式（Playwright/Chromium 渲染，标准 CSS）
PDF_STYLES = """
@page {
    size: A4;
    margin: 2cm;
}
body {
    font-family: "WenQuanYi Zen Hei", "Noto Sans SC", "SimHei", "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: 12px;
    color: #333;
    line-height: 1.6;
}
h1 { font-size: 20px; text-align: center; margin-bottom: 4px; color: #1a1a1a; }
h2 { font-size: 16px; margin-top: 20px; padding-bottom: 6px; border-bottom: 2px solid #0891B2; color: #0891B2; }
h3 { font-size: 14px; margin-top: 14px; color: #333; }
.meta { text-align: center; color: #666; font-size: 11px; margin-bottom: 20px; }
table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 11px; }
th { background: #0891B2; color: white; padding: 8px 6px; text-align: left; font-weight: 600; }
td { padding: 7px 6px; border-bottom: 1px solid #e5e7eb; }
tr:nth-child(even) td { background: #f8fafc; }
.status-high { color: #dc2626; font-weight: 600; }
.status-low { color: #2563eb; font-weight: 600; }
.status-abnormal { color: #d97706; font-weight: 600; }
.interpretation {
    white-space: pre-wrap;
    word-break: break-all;
    hyphens: auto;
    word-wrap: break-word;
    max-width: 100%;
    overflow-wrap: break-word;
}
.interpretation p { margin: 6px 0; }
.interpretation h2 { margin-top: 14px; margin-bottom: 6px; }
.interpretation h3 { margin-top: 10px; margin-bottom: 4px; }
.interpretation ul, .interpretation ol { margin: 4px 0; padding-left: 20px; }
.interpretation li { margin-bottom: 2px; }
.disclaimer { margin-top: 30px; padding: 10px; background: #fffbeb; border: 1px solid #fbbf24; border-radius: 4px; font-size: 10px; color: #92400e; }
.footer { margin-top: 20px; text-align: right; font-size: 10px; color: #999; }
"""


_GENDER_MAP = {"male": "男", "female": "女", "unknown": "未知"}


def _translate_gender(gender: str | None) -> str:
    """将性别字段翻译为中文"""
    if not gender:
        return ""
    return _GENDER_MAP.get(gender, gender)


def _get_pdf_styles() -> str:
    """返回 PDF 样式"""
    return PDF_STYLES


class ExportService:
    """数据导出服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_medical_check_pdf(self, check_id: int) -> bytes:
        """导出单次检验报告 PDF"""
        # 加载数据
        result = await self.db.execute(
            select(MedicalCheck)
            .options(selectinload(MedicalCheck.details))
            .where(MedicalCheck.medical_id == check_id)
        )
        check = result.scalar_one_or_none()
        if not check:
            raise ValueError("检验报告不存在")

        patient = await self._get_patient(check.patient_id)

        # 构建 HTML
        html = self._render_medical_check_html(check, patient)
        return await self._html_to_pdf(html)

    async def export_medical_exam_pdf(self, exam_id: int) -> bytes:
        """导出单次检查报告 PDF"""
        result = await self.db.execute(
            select(MedicalExam).where(MedicalExam.exam_id == exam_id)
        )
        exam = result.scalar_one_or_none()
        if not exam:
            raise ValueError("检查报告不存在")

        patient = await self._get_patient(exam.patient_id)
        html = self._render_medical_exam_html(exam, patient)
        return await self._html_to_pdf(html)

    async def export_pathology_report_pdf(self, report_id: int) -> bytes:
        """导出单次病理报告 PDF"""
        result = await self.db.execute(
            select(PathologyReport)
            .options(selectinload(PathologyReport.ihc_markers))
            .where(PathologyReport.report_id == report_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            raise ValueError("病理报告不存在")

        patient = await self._get_patient(report.patient_id)
        html = self._render_pathology_report_html(report, patient)
        return await self._html_to_pdf(html)

    async def export_patient_timeline_pdf(self, patient_id: int) -> bytes:
        """导出时间线 PDF"""
        from app.services import timeline_aggregator
        from app.schemas.timeline import UnifiedTimelineQuery

        patient = await self._get_patient(patient_id)
        if not patient:
            raise ValueError("患者不存在")

        query = UnifiedTimelineQuery(patient_id=patient_id, limit=100)
        events = await timeline_aggregator.fetch_unified_timeline(self.db, query)

        html = self._render_timeline_html(patient, events)
        return await self._html_to_pdf(html)

    async def export_patient_summary_pdf(self, patient_id: int) -> bytes:
        """导出完整病历 PDF"""
        patient = await self._get_patient(patient_id)
        if not patient:
            raise ValueError("患者不存在")

        # 加载各类报告
        checks_result = await self.db.execute(
            select(MedicalCheck)
            .options(selectinload(MedicalCheck.details))
            .where(MedicalCheck.patient_id == patient_id)
            .order_by(MedicalCheck.medical_date.desc())
            .limit(20)
        )
        checks = checks_result.scalars().all()

        exams_result = await self.db.execute(
            select(MedicalExam)
            .where(MedicalExam.patient_id == patient_id)
            .order_by(MedicalExam.medical_date.desc())
            .limit(10)
        )
        exams = exams_result.scalars().all()

        medications_result = await self.db.execute(
            select(Medication)
            .where(Medication.patient_id == patient_id)
            .order_by(Medication.start_date.desc())
        )
        medications = medications_result.scalars().all()

        html = self._render_summary_html(patient, checks, exams, medications)
        return await self._html_to_pdf(html)

    async def _get_patient(self, patient_id: int) -> Optional[Patient]:
        result = await self.db.execute(
            select(Patient).where(Patient.patient_id == patient_id)
        )
        return result.scalar_one_or_none()

    # 来源类型中文映射
    SOURCE_TYPE_MAP = {
        "timeline_event": "时间线事件",
        "medical_check": "检验报告",
        "medical_exam": "检查报告",
        "pathology_report": "病理报告",
        "medication": "用药记录",
        "event": "事件",
    }

    # 用药状态中文映射
    MED_STATUS_MAP = {
        "active": "使用中",
        "paused": "暂停",
        "discontinued": "已停用",
        "completed": "已完成",
    }

    def _render_medical_check_html(self, check: MedicalCheck, patient: Optional[Patient]) -> str:
        """渲染检验报告 HTML"""
        patient_info = ""
        if patient:
            patient_info = f"{_translate_gender(patient.gender)}，{calculate_age(patient.birth_date) or ''}岁"

        details = []
        for d in check.details:
            status_class = f"status-{d.index_status}" if d.index_status in ("high", "low", "abnormal") else ""
            status_label = {"high": "↑偏高", "low": "↓偏低", "abnormal": "异常"}.get(d.index_status, "正常")
            details.append({
                "index_name": d.index_name or '',
                "index_value": str(d.index_value or ''),
                "index_unit": d.index_unit or '',
                "reference_value": d.reference_value or '-',
                "status_class": status_class,
                "status_label": status_label,
            })

        interpretation_html = ""
        if check.interpretation:
            interp = md.markdown(
                check.interpretation,
                extensions=["tables", "fenced_code"],
            )
            interp = _sanitize_html(interp)
            interpretation_html = interp

        template = jinja_env.get_template("medical_check.html")
        return template.render(
            styles=_get_pdf_styles(),
            hospital=check.hospital or '',
            medical_date=check.medical_date.isoformat(),
            patient_info=patient_info,
            details=details,
            interpretation_html=interpretation_html,
            now=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

    def _render_medical_exam_html(self, exam: MedicalExam, patient: Optional[Patient]) -> str:
        """渲染检查报告 HTML"""
        patient_info = ""
        if patient:
            patient_info = f"{_translate_gender(patient.gender)}，{calculate_age(patient.birth_date) or ''}岁"

        interpretation_html = ""
        if exam.interpretation:
            interp = md.markdown(exam.interpretation, extensions=["tables", "fenced_code"])
            interpretation_html = _sanitize_html(interp)

        template = jinja_env.get_template("medical_exam.html")
        return template.render(
            styles=_get_pdf_styles(),
            hospital=exam.hospital or '',
            medical_date=(exam.medical_date.isoformat() if exam.medical_date else ''),
            patient_info=patient_info,
            title=exam.title or '',
            exam_type=exam.exam_type or '',
            exam_info=exam.exam_info or '',
            exam_diag=exam.exam_diag or '',
            comment=exam.comment or '',
            interpretation_html=interpretation_html,
            now=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

    def _render_pathology_report_html(self, report: PathologyReport, patient: Optional[Patient]) -> str:
        """渲染病理报告 HTML"""
        patient_info = ""
        if patient:
            patient_info = f"{_translate_gender(patient.gender)}，{calculate_age(patient.birth_date) or ''}岁"

        ihc_markers = []
        for m in (report.ihc_markers or []):
            ihc_markers.append({
                "marker_name": m.marker_name or '',
                "result": m.result or '',
                "intensity": m.intensity or '',
                "percentage": m.percentage or '',
            })

        interpretation_html = ""
        if report.interpretation:
            interp = md.markdown(report.interpretation, extensions=["tables", "fenced_code"])
            interpretation_html = _sanitize_html(interp)

        template = jinja_env.get_template("pathology_report.html")
        return template.render(
            styles=_get_pdf_styles(),
            hospital=report.hospital or '',
            report_date=(report.report_date.isoformat() if report.report_date else ''),
            patient_info=patient_info,
            report_title=report.report_title or '',
            diagnosis=report.diagnosis or '',
            cancer_type=report.cancer_type or '',
            stage=report.stage or '',
            histology_type=report.histology_type or '',
            ihc_markers=ihc_markers,
            immunohistochemistry=report.immunohistochemistry or '',
            gene_testing=report.gene_testing or '',
            comment=report.comment or '',
            interpretation_html=interpretation_html,
            now=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

    def _render_timeline_html(self, patient: Patient, events: list) -> str:
        """渲染时间线 HTML"""
        event_list = []
        for e in events:
            source = self.SOURCE_TYPE_MAP.get(e.source_type, e.source_type or '')
            event_list.append({
                "event_date": e.event_date,
                "source": source,
                "title": e.title,
                "category": CATEGORY_LABELS.get(e.category, e.category or ''),
            })

        template = jinja_env.get_template("timeline.html")
        return template.render(
            styles=_get_pdf_styles(),
            patient_name="患者",
            events=event_list,
            now=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

    def _render_summary_html(
        self,
        patient: Patient,
        checks: list,
        exams: list,
        medications: list,
    ) -> str:
        """渲染完整病历 HTML"""
        patient_info = f"{_translate_gender(patient.gender)}，{calculate_age(patient.birth_date) or ''}岁"

        # 诊断
        diagnosis = ""
        if patient.medical_history:
            if isinstance(patient.medical_history, dict):
                diagnosis = patient.medical_history.get("diagnosis", "")
            elif isinstance(patient.medical_history, str):
                diagnosis = patient.medical_history[:200]

        # 用药
        med_list = []
        for m in medications:
            med_list.append({
                "medication_name": m.medication_name,
                "route": m.route or '-',
                "dosage": m.dosage or '',
                "frequency": m.frequency or '',
                "start_date": m.start_date.isoformat() if m.start_date else '',
                "status_label": self.MED_STATUS_MAP.get(m.status, m.status),
            })

        # 检验报告
        check_list = []
        for check in checks[:5]:
            detail_list = []
            for d in check.details:
                status_class = f"status-{d.index_status}" if d.index_status in ("high", "low", "abnormal") else ""
                detail_list.append({
                    "index_name": d.index_name,
                    "index_value": str(d.index_value or ''),
                    "index_unit": d.index_unit or '',
                    "reference_value": d.reference_value or '-',
                    "status_class": status_class,
                })
            check_list.append({
                "medical_date": check.medical_date.isoformat(),
                "hospital": check.hospital or '检验报告',
                "details": detail_list,
            })

        # 检查报告
        exam_list = []
        for e in exams:
            exam_list.append({
                "exam_date": e.medical_date.isoformat() if e.medical_date else '',
                "exam_type": e.exam_type or '',
                "exam_info": e.exam_info or '',
                "exam_diag": e.exam_diag or '',
            })

        template = jinja_env.get_template("patient_summary.html")
        return template.render(
            styles=_get_pdf_styles(),
            patient_name="患者",
            patient_info=patient_info,
            gender=_translate_gender(patient.gender) or '-',
            age=calculate_age(patient.birth_date) or '-',
            diagnosis=diagnosis or '-',
            medications=med_list,
            checks=check_list,
            exams=exam_list,
            now=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

    async def _html_to_pdf(self, html: str) -> bytes:
        """将 HTML 转换为 PDF（Playwright/Chromium 渲染，通过线程池调用同步 API）"""
        return await asyncio.to_thread(_sync_html_to_pdf, html)
