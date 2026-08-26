import pytest
from app.services import export_service


@pytest.fixture(scope="module", autouse=True)
def close_browser_after_tests():
    yield
    export_service.close_playwright_browser()


def test_get_pdf_styles_no_placeholder():
    """PDF 样式不应包含旧引擎的占位符"""
    styles = export_service._get_pdf_styles()
    assert "__FONT_FAMILY__" not in styles
    assert "__FONT_FACE_CSS__" not in styles
    assert "font-family" in styles


def test_sync_html_to_pdf_returns_valid_pdf():
    """_sync_html_to_pdf 应返回以 %PDF 开头的有效 PDF 字节"""
    html = """<html><head><style>body { font-family: sans-serif; }</style></head>
    <body><h1>测试报告</h1><p>Test content</p></body></html>"""
    pdf_bytes = export_service._sync_html_to_pdf(html)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 100
    assert pdf_bytes[:4] == b"%PDF"


def test_sync_html_to_pdf_chinese_content():
    """_sync_html_to_pdf 应正确处理中文内容"""
    html = """<html><head><style>
    body { font-family: "SimHei", "Noto Sans SC", sans-serif; }
    </style></head>
    <body>
    <h1>检验报告</h1>
    <table>
        <tr><th>指标名称</th><th>结果</th><th>参考范围</th></tr>
        <tr><td>白细胞</td><td class="status-high">12.5 ↑</td><td>4.0-10.0</td></tr>
    </table>
    <div class="disclaimer">本报告仅供参考，不作为医疗诊断依据。</div>
    </body></html>"""
    pdf_bytes = export_service._sync_html_to_pdf(html)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes[:4] == b"%PDF"


def test_render_summary_html_with_exams():
    """完整病历渲染：含检查报告时不应抛错（回归：MedicalExam 字段名为 medical_date）"""
    from datetime import date
    from app.models.patient import Patient
    from app.models.medical import MedicalExam
    from app.services.export_service import ExportService

    patient = Patient(
        gender="male",
        birth_date=date(1990, 1, 1),
        medical_history={"diagnosis": "测试诊断"},
    )
    exam = MedicalExam(
        medical_date=date(2026, 8, 1),
        exam_type="CT",
        exam_info="检查所见",
        exam_diag="诊断意见",
    )
    service = ExportService(db=None)  # _render_summary_html 为纯渲染方法，不触库
    html = service._render_summary_html(patient, checks=[], exams=[exam], medications=[])

    assert "检查报告" in html
    assert "CT" in html
    assert "2026-08-01" in html
