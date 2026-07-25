#!/usr/bin/env python3
"""
PDF文档转换器
将PDF文档转换为HTML格式
"""

import os
import logging
from io import BytesIO
from typing import Tuple, Optional

from .base import BaseConverter, HTMLWrapper, ConversionError

logger = logging.getLogger(__name__)


class PdfConverter(BaseConverter):
    """PDF文档转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['pdf']
    
    def is_supported(self, file_type: str) -> bool:
        """检查文件类型是否支持转换"""
        return file_type.lower() in self.supported_formats
    
    def convert_to_html(self, file_path: str, file_type: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """转换PDF文档为HTML"""
        try:
            # 验证文件
            is_valid, error_msg = self.validate_file(file_path)
            if not is_valid:
                return False, None, error_msg
            
            # 验证PDF文件格式
            if not self._validate_pdf_file(file_path):
                return False, None, "不是有效的PDF文件"

            file_name = os.path.basename(file_path)

            # 方法1: 尝试使用 PDFium 进行高质量转换（包含图片和排版）
            try:
                return self._convert_with_pdfium(file_path, file_name)
            except ImportError:
                logger.info("pypdfium2 未安装，尝试其他方法")
                
            # 方法2: 使用pdfplumber（仅文本）
            try:
                return self._convert_with_pdfplumber(file_path, file_name)
            except ImportError:
                logger.info("pdfplumber未安装，使用基础查看器")
                
            # 方法3: 基础查看器
            return self._create_pdf_viewer_html(file_path)

        except Exception as e:
            logger.error(f"转换PDF失败: {str(e)}")
            # 出错时也返回基础查看器
            return self._create_pdf_viewer_html(file_path)
    
    def _validate_pdf_file(self, file_path: str) -> bool:
        """验证PDF文件格式"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                return header.startswith(b'%PDF')
        except Exception:
            return False
    
    def _convert_with_pdfium(self, file_path: str, file_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """使用 PDFium 渲染页面并提取可搜索文本。"""
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(file_path)
        content_parts = []
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                try:
                    content_parts.append(f"<div class='pdf-page' data-page='{page_num + 1}'>")
                    content_parts.append(f"<div class='pdf-page-header'>第 {page_num + 1} 页</div>")

                    try:
                        bitmap = page.render(scale=2.0)
                        image = bitmap.to_pil()
                        image_buffer = BytesIO()
                        image.save(image_buffer, format="PNG")

                        import base64
                        img_base64 = base64.b64encode(image_buffer.getvalue()).decode('utf-8')
                        content_parts.append(f"""
                        <div class='pdf-page-image'>
                            <img src="data:image/png;base64,{img_base64}"
                                 alt="第 {page_num + 1} 页"
                                 class="pdf-rendered-page"
                                 onclick="togglePageFullscreen(this)">
                        </div>
                        """)

                        text_page = page.get_textpage()
                        text = text_page.get_text_range()
                        if text.strip():
                            content_parts.append(f"""
                            <div class='pdf-text-content' style='display: none;'>
                                <h4>文本内容（用于搜索和复制）:</h4>
                                <div class='pdf-text'>
                                    {HTMLWrapper.escape_html(text)}
                                </div>
                            </div>
                            """)
                    except Exception as img_error:
                        logger.warning(f"PDF页面图片渲染失败: {img_error}")
                        text_page = page.get_textpage()
                        text = text_page.get_text_range()
                        if text.strip():
                            content_parts.append("<div class='pdf-text-fallback'>")
                            paragraphs = text.split('\n\n')
                            for paragraph in paragraphs:
                                if paragraph.strip():
                                    content_parts.append(f"<p>{HTMLWrapper.escape_html(paragraph.strip())}</p>")
                            content_parts.append("</div>")
                        else:
                            content_parts.append("<p class='no-content'>此页面无法显示内容</p>")

                    content_parts.append("</div>")
                finally:
                    page.close()
        finally:
            doc.close()

        if content_parts:
            html_content = "\n".join(content_parts)
            full_html = self._wrap_pdf_html(html_content, f"PDF预览 - {file_name}")
            return True, full_html, None
        else:
            # 如果没有内容，使用基础查看器
            return self._create_pdf_viewer_html(file_path)
    
    def _convert_with_pdfplumber(self, file_path: str, file_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """使用pdfplumber进行转换"""
        import pdfplumber

        content_parts = []

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()

                if text and text.strip():
                    content_parts.append(f"<div class='pdf-page' data-page='{page_num}'>")
                    content_parts.append(f"<div class='pdf-page-header'>第 {page_num} 页</div>")
                    content_parts.append("<div class='pdf-text-content'>")

                    # 按段落分割文本
                    paragraphs = text.split('\n\n')
                    for paragraph in paragraphs:
                        if paragraph.strip():
                            content_parts.append(f"<p>{HTMLWrapper.escape_html(paragraph.strip())}</p>")

                    content_parts.append("</div></div>")

        if content_parts:
            html_content = "\n".join(content_parts)
            full_html = self._wrap_pdf_html(html_content, f"PDF预览 - {file_name}")
            return True, full_html, None
        else:
            return self._create_pdf_viewer_html(file_path)
    
    def _create_pdf_viewer_html(self, file_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """创建PDF查看器HTML页面（当转换失败时的回退方案）"""
        try:
            if not self._validate_pdf_file(file_path):
                return False, None, "不是有效的PDF文件"

            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)

            # 创建一个基础的PDF查看器HTML页面
            html_content = f"""
            <div class="pdf-page">
                <div class="pdf-page-header">PDF文档无法预览</div>
                <div style="padding: 20px; text-align: center;">
                    <p style="color: #666; margin-bottom: 20px;">无法提取PDF内容进行预览。</p>
                    <div style="margin-bottom: 20px;">
                        <button onclick="downloadPdf()" style="background: #007bff; color: white; border: none; padding: 12px 24px; border-radius: 5px; cursor: pointer; margin: 5px; font-size: 16px;">
                            📥 下载PDF文件
                        </button>
                    </div>

                    <div style="margin-bottom: 20px;">
                        <button onclick="tryOpenPdf()" style="background: #28a745; color: white; border: none; padding: 12px 24px; border-radius: 5px; cursor: pointer; margin: 5px; font-size: 16px;">
                            🔗 在新窗口打开
                        </button>
                    </div>

                    <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 5px;">
                        <h4>💡 使用提示</h4>
                        <ul style="text-align: left; display: inline-block;">
                            <li>点击"下载PDF文件"保存到设备后查看</li>
                            <li>点击"在新窗口打开"尝试浏览器预览</li>
                            <li>如果是移动设备，建议下载后使用PDF阅读器打开</li>
                        </ul>
                    </div>
                </div>
            </div>

            <script>
                function downloadPdf() {{
                    console.log('触发PDF下载');
                    const link = document.createElement('a');
                    link.href = window.location.href.replace('/preview', '/download');
                    link.download = '{HTMLWrapper.escape_html(file_name)}';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                }}

                function tryOpenPdf() {{
                    console.log('尝试在新窗口打开PDF');
                    let pdfUrl = window.location.href;

                    if (pdfUrl.includes('/preview')) {{
                        pdfUrl = pdfUrl.replace('/preview', '/preview');
                    }}

                    const newWindow = window.open(pdfUrl, '_blank');
                    if (!newWindow) {{
                        alert('弹出窗口被阻止，请允许弹出窗口后重试');
                    }}
                }}

                document.addEventListener('DOMContentLoaded', function() {{
                    console.log('PDF基础查看器加载完成');
                }});
            </script>
            """

            full_html = self._wrap_pdf_html(html_content, f"PDF查看器 - {file_name}")
            return True, full_html, None

        except Exception as e:
            logger.error(f"创建PDF查看器HTML失败: {str(e)}")
            return False, None, str(e)

    def _wrap_pdf_html(self, content: str, title: str) -> str:
        """为PDF内容包装HTML页面"""
        escaped_title = HTMLWrapper.escape_html(title)

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes, minimum-scale=0.5, maximum-scale=3.0">
            <meta name="format-detection" content="telephone=no">
            <meta name="apple-mobile-web-app-capable" content="yes">
            <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
            <title>{escaped_title}</title>
            <style>
                * {{
                    box-sizing: border-box;
                }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 5px;
                    background: #f8f9fa;
                    color: #333;
                    font-size: 16px;
                    -webkit-text-size-adjust: 100%;
                }}

                .pdf-page {{
                    background: white;
                    margin-bottom: 10px;
                    border-radius: 4px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}

                .pdf-page-header {{
                    background: #f8f9fa;
                    color: #666;
                    padding: 5px 10px;
                    font-weight: normal;
                    font-size: 12px;
                    border-bottom: 1px solid #eee;
                }}

                .pdf-page-image {{
                    text-align: center;
                    padding: 5px;
                    background: white;
                }}

                .pdf-rendered-page {{
                    max-width: 100%;
                    height: auto;
                    border: none;
                    cursor: pointer;
                    transition: transform 0.3s ease;
                }}

                .pdf-rendered-page:hover {{
                    transform: scale(1.02);
                }}

                .pdf-rendered-page:fullscreen {{
                    max-width: 100vw;
                    max-height: 100vh;
                    object-fit: contain;
                    background: black;
                }}

                .pdf-text-content {{
                    padding: 10px;
                    border-top: 1px solid #eee;
                    display: none;
                }}

                .pdf-text-content h4 {{
                    color: #495057;
                    margin-bottom: 5px;
                    font-size: 12px;
                }}

                .pdf-text {{
                    background: #f8f9fa;
                    padding: 8px;
                    border-radius: 4px;
                    white-space: pre-wrap;
                    font-family: monospace;
                    font-size: 12px;
                    max-height: 150px;
                    overflow-y: auto;
                }}

                .pdf-text-fallback {{
                    padding: 10px;
                }}

                .pdf-text-fallback p {{
                    margin-bottom: 10px;
                    text-align: justify;
                    line-height: 1.6;
                    font-size: 14px;
                }}

                .no-content {{
                    text-align: center;
                    color: #6c757d;
                    font-style: italic;
                    padding: 20px 10px;
                }}

                @media (max-width: 768px) {{
                    body {{
                        padding: 2px;
                        font-size: 14px;
                    }}

                    .pdf-page-header {{
                        padding: 3px 8px;
                        font-size: 11px;
                    }}

                    .pdf-page-image {{
                        padding: 2px;
                    }}

                    .pdf-rendered-page {{
                        max-width: 100%;
                    }}
                }}
            </style>
        </head>
        <body>
            {content}

            <script>
                function togglePageFullscreen(img) {{
                    if (!document.fullscreenElement) {{
                        img.requestFullscreen().catch(err => {{
                            console.log('无法进入全屏模式:', err);
                        }});
                    }} else {{
                        document.exitFullscreen();
                    }}
                }}

                // 键盘事件支持
                document.addEventListener('keydown', function(e) {{
                    if (e.key === 'Escape' && document.fullscreenElement) {{
                        document.exitFullscreen();
                    }}
                }});

                // 页面加载完成后的处理
                document.addEventListener('DOMContentLoaded', function() {{
                    console.log('PDF预览页面加载完成');

                    // 检查是否有内容
                    const pages = document.querySelectorAll('.pdf-page');
                    if (pages.length === 0) {{
                        document.body.innerHTML = `
                            <div style="text-align: center; padding: 50px;">
                                <h2>⚠️ PDF预览失败</h2>
                                <p>无法显示PDF内容，请尝试下载文件查看。</p>
                            </div>
                        `;
                    }}
                }});
            </script>
        </body>
        </html>
        """
