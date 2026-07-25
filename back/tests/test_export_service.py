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
