"""Regression coverage for the PDFium-based PDF preview path."""

import pypdfium2 as pdfium

from app.utils.converters.pdf_converter import PdfConverter


def test_pdfium_pdf_preview_renders_generated_page(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    document = pdfium.PdfDocument.new()
    try:
        page = document.new_page(200, 300)
        page.close()
        document.save(pdf_path)
    finally:
        document.close()

    converter = PdfConverter()
    success, html, error = converter.convert_to_html(str(pdf_path), "pdf")

    assert success is True
    assert error is None
    assert "data:image/png;base64," in html
    assert "data-page='1'" in html
