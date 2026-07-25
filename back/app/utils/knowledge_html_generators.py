"""
知识库HTML生成器模块
包含各种文件类型的HTML预览页面生成功能
"""
from app.utils.knowledge_file_utils import format_file_size


def create_fullscreen_image_preview_html(document, image_url):
    """
    创建全屏图片预览HTML

    Args:
        document: 文档对象
        image_url: 图片URL

    Returns:
        str: HTML内容
    """
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
        <title>{document.doc_name}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            html, body {{
                height: 100%;
                overflow: hidden;
                background: #000;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}

            .preview-container {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: #000;
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: auto;
            }}

            .image-wrapper {{
                width: 100%;
                height: 100%;
                display: flex;
                align-items: flex-start;
                justify-content: center;
                overflow: auto;
                padding: 0;
            }}

            .preview-image {{
                width: 100%;
                height: auto;
                max-width: none;
                display: block;
                object-fit: contain;
            }}

            /* 隐藏浮动按钮的样式 */
            .floating-buttons,
            .fab,
            .add-button,
            .upload-button,
            [class*="float"],
            [class*="fab"],
            [id*="float"],
            [id*="fab"] {{
                display: none !important;
                visibility: hidden !important;
            }}

            /* 移动端优化 */
            @media (max-width: 768px) {{
                .preview-image {{
                    width: 100vw;
                    height: auto;
                }}
            }}

            /* 加载提示 */
            .loading {{
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                color: #fff;
                font-size: 16px;
            }}
        </style>
    </head>
    <body>
        <div class="preview-container">
            <div class="image-wrapper">
                <div class="loading" id="loading">加载中...</div>
                <img class="preview-image"
                     src="{image_url}"
                     alt="{document.doc_name}"
                     onload="document.getElementById('loading').style.display='none'"
                     onerror="document.getElementById('loading').innerHTML='图片加载失败'">
            </div>
        </div>

        <script>
            // 隐藏所有可能的浮动按钮
            function hideFloatingButtons() {{
                const selectors = [
                    '.floating-buttons', '.fab', '.add-button', '.upload-button',
                    '[class*="float"]', '[class*="fab"]', '[id*="float"]', '[id*="fab"]'
                ];

                selectors.forEach(selector => {{
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {{
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                    }});
                }});

                // 也隐藏父窗口的浮动按钮
                try {{
                    if (window.parent && window.parent.document) {{
                        selectors.forEach(selector => {{
                            const elements = window.parent.document.querySelectorAll(selector);
                            elements.forEach(el => {{
                                el.style.display = 'none';
                                el.style.visibility = 'hidden';
                            }});
                        }});
                    }}
                }} catch(e) {{
                    // 跨域限制，忽略错误
                }}
            }}

            // 页面加载完成后执行
            document.addEventListener('DOMContentLoaded', hideFloatingButtons);

            // 定期检查并隐藏浮动按钮
            setInterval(hideFloatingButtons, 1000);

            // 阻止右键菜单（可选）
            document.addEventListener('contextmenu', function(e) {{
                e.preventDefault();
            }});
        </script>
    </body>
    </html>
    """
    return html_content


def create_text_preview_html(document, content, file_ext):
    """
    创建文本文件的HTML预览（全屏版本）

    Args:
        document: 文档对象
        content: 文件内容
        file_ext: 文件扩展名

    Returns:
        str: HTML内容
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{document.doc_name}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            html, body {{
                height: 100%;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                background: #f5f5f5;
            }}

            .container {{
                width: 100vw;
                height: 100vh;
                background: white;
                display: flex;
                flex-direction: column;
                /* 移除圆角和阴影 */
            }}

            .header {{
                background: #2c3e50;
                color: white;
                padding: 20px;
                flex-shrink: 0;
                border-bottom: 2px solid #34495e;
            }}

            .header h1 {{
                margin: 0 0 10px 0;
                font-size: 20px;
                font-weight: 600;
            }}

            .header p {{
                margin: 0;
                opacity: 0.9;
                font-size: 14px;
            }}

            .content {{
                flex: 1;
                padding: 20px;
                overflow-y: auto;
                white-space: pre-wrap;
                font-family: 'Courier New', 'Monaco', 'Menlo', monospace;
                font-size: 14px;
                line-height: 1.5;
                background: #fff;
            }}

            /* 隐藏浮动按钮 */
            .floating-buttons,
            .fab,
            .add-button,
            .upload-button,
            [class*="float"],
            [class*="fab"],
            [id*="float"],
            [id*="fab"] {{
                display: none !important;
                visibility: hidden !important;
            }}

            @media (max-width: 768px) {{
                .header {{
                    padding: 15px;
                }}
                .header h1 {{
                    font-size: 18px;
                }}
                .content {{
                    padding: 15px;
                    font-size: 12px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{document.doc_name}</h1>
                <p>文件类型: {file_ext.upper()} | 大小: {document.file_size} 字节</p>
            </div>
            <div class="content">{content}</div>
        </div>

        <script>
            // 隐藏浮动按钮
            function hideFloatingButtons() {{
                const selectors = [
                    '.floating-buttons', '.fab', '.add-button', '.upload-button',
                    '[class*="float"]', '[class*="fab"]', '[id*="float"]', '[id*="fab"]'
                ];

                selectors.forEach(selector => {{
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {{
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                    }});
                }});

                try {{
                    if (window.parent && window.parent.document) {{
                        selectors.forEach(selector => {{
                            const elements = window.parent.document.querySelectorAll(selector);
                            elements.forEach(el => {{
                                el.style.display = 'none';
                                el.style.visibility = 'hidden';
                            }});
                        }});
                    }}
                }} catch(e) {{
                    // 跨域限制，忽略错误
                }}
            }}

            document.addEventListener('DOMContentLoaded', hideFloatingButtons);
            setInterval(hideFloatingButtons, 1000);
        </script>
    </body>
    </html>
    """
    return html_content


def create_office_preview_html(document, file_ext):
    """
    创建Office文档的简化预览HTML（全屏版本）

    Args:
        document: 文档对象
        file_ext: 文件扩展名

    Returns:
        str: HTML内容
    """
    file_type_names = {
        'doc': 'Word文档',
        'docx': 'Word文档',
        'xls': 'Excel表格',
        'xlsx': 'Excel表格',
        'ppt': 'PowerPoint演示文稿',
        'pptx': 'PowerPoint演示文稿'
    }

    file_type_name = file_type_names.get(file_ext, 'Office文档')
    size_str = format_file_size(document.file_size or 0)

    # 为PPT/PPTX文件提供特殊的转换状态信息
    if file_ext in ['ppt', 'pptx']:
        conversion_status_html = f"""
        <div class="suggestions">
            <h3>转换建议</h3>
            <div class="suggestion-list">
                <div class="suggestion-item">
                    <span class="suggestion-icon">🔄</span>
                    <div class="suggestion-content">
                        <strong>格式转换</strong>
                        <p>如果是.ppt文件，建议转换为.pptx格式以获得更好的支持</p>
                    </div>
                </div>
                <div class="suggestion-item">
                    <span class="suggestion-icon">💻</span>
                    <div class="suggestion-content">
                        <strong>本地查看</strong>
                        <p>下载文件后使用PowerPoint、LibreOffice或WPS打开</p>
                    </div>
                </div>
            </div>
        </div>
        """
    else:
        conversion_status_html = ""

    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{document.doc_name}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            html, body {{
                height: 100%;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f5f5;
                color: #333;
            }}

            .container {{
                width: 100vw;
                height: 100vh;
                background: white;
                display: flex;
                flex-direction: column;
                /* 移除圆角和阴影 */
            }}

            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
                flex-shrink: 0;
            }}

            .header h1 {{
                margin: 0 0 10px 0;
                font-size: 24px;
                font-weight: 600;
            }}

            .header p {{
                margin: 0;
                opacity: 0.9;
                font-size: 16px;
            }}

            .content {{
                flex: 1;
                padding: 40px;
                text-align: center;
                overflow-y: auto;
            }}

            .file-icon {{
                font-size: 64px;
                margin-bottom: 20px;
                color: #667eea;
            }}

            .file-info {{
                background: #f8f9fa;
                padding: 20px;
                margin: 20px 0;
                /* 移除圆角 */
            }}

            .info-row {{
                display: flex;
                justify-content: space-between;
                margin: 10px 0;
                padding: 8px 0;
                border-bottom: 1px solid #e9ecef;
            }}

            .info-row:last-child {{
                border-bottom: none;
            }}

            .download-btn {{
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                font-weight: 500;
                margin-top: 20px;
                transition: background 0.3s;
                /* 移除圆角 */
            }}

            .download-btn:hover {{
                background: #5a67d8;
            }}

            .note {{
                color: #6c757d;
                font-size: 14px;
                margin-top: 20px;
                line-height: 1.5;
            }}

            /* 转换状态样式 */
            .conversion-attempts {{
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                padding: 20px;
                margin: 20px 0;
            }}

            .conversion-attempts h3 {{
                margin: 0 0 15px 0;
                color: #856404;
                font-size: 16px;
            }}

            .attempt-list {{
                list-style: none;
                padding: 0;
                margin: 0;
            }}

            .attempt-item {{
                display: flex;
                align-items: center;
                padding: 8px 0;
                border-bottom: 1px solid #f5e79e;
            }}

            .attempt-item:last-child {{
                border-bottom: none;
            }}

            .attempt-icon {{
                margin-right: 10px;
                font-size: 14px;
            }}

            .attempt-text {{
                color: #856404;
                font-size: 14px;
            }}

            .suggestions {{
                background: #d1ecf1;
                border: 1px solid #bee5eb;
                padding: 20px;
                margin: 20px 0;
            }}

            .suggestions h3 {{
                margin: 0 0 15px 0;
                color: #0c5460;
                font-size: 16px;
            }}

            .suggestion-list {{
                list-style: none;
                padding: 0;
                margin: 0;
            }}

            .suggestion-item {{
                display: flex;
                align-items: flex-start;
                padding: 12px 0;
                border-bottom: 1px solid #b8daff;
            }}

            .suggestion-item:last-child {{
                border-bottom: none;
            }}

            .suggestion-icon {{
                margin-right: 15px;
                font-size: 18px;
                margin-top: 2px;
            }}

            .suggestion-content strong {{
                display: block;
                color: #0c5460;
                font-size: 14px;
                margin-bottom: 4px;
            }}

            .suggestion-content p {{
                margin: 0;
                color: #0c5460;
                font-size: 13px;
                line-height: 1.4;
            }}

            /* 隐藏浮动按钮 */
            .floating-buttons,
            .fab,
            .add-button,
            .upload-button,
            [class*="float"],
            [class*="fab"],
            [id*="float"],
            [id*="fab"] {{
                display: none !important;
                visibility: hidden !important;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{document.doc_name}</h1>
                <p>{file_type_name}预览</p>
            </div>
            <div class="content">
                <div class="file-icon">📄</div>
                <h2>文档信息</h2>
                <div class="file-info">
                    <div class="info-row">
                        <span><strong>文件名：</strong></span>
                        <span>{document.file_name}</span>
                    </div>
                    <div class="info-row">
                        <span><strong>文件类型：</strong></span>
                        <span>{file_type_name} (.{file_ext})</span>
                    </div>
                    <div class="info-row">
                        <span><strong>文件大小：</strong></span>
                        <span>{size_str}</span>
                    </div>
                    <div class="info-row">
                        <span><strong>上传时间：</strong></span>
                        <span>{document.created_at.strftime('%Y-%m-%d %H:%M:%S')}</span>
                    </div>
                </div>

                {conversion_status_html}

                <p class="note">
                    此文档需要在支持Office格式的应用中打开以获得最佳预览效果。<br>
                    您可以下载文档到本地，使用Microsoft Office、WPS或其他兼容软件打开。
                </p>
                <a href="/api/knowledge/documents/{document.doc_id}/download" class="download-btn">
                    📥 下载文档
                </a>
            </div>
        </div>

        <script>
            // 隐藏浮动按钮
            function hideFloatingButtons() {{
                const selectors = [
                    '.floating-buttons', '.fab', '.add-button', '.upload-button',
                    '[class*="float"]', '[class*="fab"]', '[id*="float"]', '[id*="fab"]'
                ];

                selectors.forEach(selector => {{
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {{
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                    }});
                }});

                try {{
                    if (window.parent && window.parent.document) {{
                        selectors.forEach(selector => {{
                            const elements = window.parent.document.querySelectorAll(selector);
                            elements.forEach(el => {{
                                el.style.display = 'none';
                                el.style.visibility = 'hidden';
                            }});
                        }});
                    }}
                }} catch(e) {{
                    // 跨域限制，忽略错误
                }}
            }}

            document.addEventListener('DOMContentLoaded', hideFloatingButtons);
            setInterval(hideFloatingButtons, 1000);
        </script>
    </body>
    </html>
    """
    return html_content


def create_pdf_preview_html(document):
    """
    创建PDF文档的简化预览HTML（当PDF无法直接预览时使用）

    Args:
        document: 文档对象

    Returns:
        str: HTML内容
    """
    size_str = format_file_size(document.file_size or 0)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{document.doc_name}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            html, body {{
                height: 100%;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f5f5;
                color: #333;
            }}

            .container {{
                width: 100vw;
                height: 100vh;
                background: white;
                display: flex;
                flex-direction: column;
                /* 移除圆角和阴影 */
            }}

            .header {{
                background: linear-gradient(135deg, #e53e3e 0%, #c53030 100%);
                color: white;
                padding: 30px;
                text-align: center;
                flex-shrink: 0;
            }}

            .header h1 {{
                margin: 0 0 10px 0;
                font-size: 24px;
                font-weight: 600;
            }}

            .header p {{
                margin: 0;
                opacity: 0.9;
                font-size: 16px;
            }}

            .content {{
                flex: 1;
                padding: 40px;
                text-align: center;
                overflow-y: auto;
            }}

            .file-icon {{
                font-size: 64px;
                margin-bottom: 20px;
                color: #e53e3e;
            }}

            .file-info {{
                background: #f8f9fa;
                padding: 20px;
                margin: 20px 0;
                /* 移除圆角 */
            }}

            .info-row {{
                display: flex;
                justify-content: space-between;
                margin: 10px 0;
                padding: 8px 0;
                border-bottom: 1px solid #e9ecef;
            }}

            .info-row:last-child {{
                border-bottom: none;
            }}

            .download-btn {{
                display: inline-block;
                background: #e53e3e;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                font-weight: 500;
                margin-top: 20px;
                transition: background 0.3s;
                /* 移除圆角 */
            }}

            .download-btn:hover {{
                background: #c53030;
            }}

            .note {{
                color: #6c757d;
                font-size: 14px;
                margin-top: 20px;
                line-height: 1.5;
            }}

            /* 隐藏浮动按钮 */
            .floating-buttons,
            .fab,
            .add-button,
            .upload-button,
            [class*="float"],
            [class*="fab"],
            [id*="float"],
            [id*="fab"] {{
                display: none !important;
                visibility: hidden !important;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{document.doc_name}</h1>
                <p>PDF文档预览</p>
            </div>
            <div class="content">
                <div class="file-icon">📄</div>
                <h2>文档信息</h2>
                <div class="file-info">
                    <div class="info-row">
                        <span><strong>文件名：</strong></span>
                        <span>{document.file_name}</span>
                    </div>
                    <div class="info-row">
                        <span><strong>文件类型：</strong></span>
                        <span>PDF文档 (.pdf)</span>
                    </div>
                    <div class="info-row">
                        <span><strong>文件大小：</strong></span>
                        <span>{size_str}</span>
                    </div>
                    <div class="info-row">
                        <span><strong>上传时间：</strong></span>
                        <span>{document.created_at.strftime('%Y-%m-%d %H:%M:%S')}</span>
                    </div>
                </div>
                <p class="note">
                    PDF文档需要在支持PDF格式的应用中打开以获得最佳预览效果。<br>
                    您可以下载文档到本地，使用Adobe Reader、浏览器或其他PDF阅读器打开。
                </p>
                <a href="/api/knowledge/documents/{document.doc_id}/download" class="download-btn">
                    📥 下载PDF
                </a>
            </div>
        </div>

        <script>
            // 隐藏浮动按钮
            function hideFloatingButtons() {{
                const selectors = [
                    '.floating-buttons', '.fab', '.add-button', '.upload-button',
                    '[class*="float"]', '[class*="fab"]', '[id*="float"]', '[id*="fab"]'
                ];

                selectors.forEach(selector => {{
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {{
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                    }});
                }});

                try {{
                    if (window.parent && window.parent.document) {{
                        selectors.forEach(selector => {{
                            const elements = window.parent.document.querySelectorAll(selector);
                            elements.forEach(el => {{
                                el.style.display = 'none';
                                el.style.visibility = 'hidden';
                            }});
                        }});
                    }}
                }} catch(e) {{
                    // 跨域限制，忽略错误
                }}
            }}

            document.addEventListener('DOMContentLoaded', hideFloatingButtons);
            setInterval(hideFloatingButtons, 1000);
        </script>
    </body>
    </html>
    """
    return html_content


def create_fullscreen_pdf_viewer_html(document, pdf_url):
    """
    创建全屏PDF查看器HTML

    Args:
        document: 文档对象
        pdf_url: PDF文件URL

    Returns:
        str: HTML内容
    """
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{document.doc_name}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            html, body {{
                height: 100%;
                overflow: hidden;
                background: #000;
            }}

            .pdf-container {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: #000;
            }}

            .pdf-viewer {{
                width: 100%;
                height: 100%;
                border: none;
                display: block;
            }}

            .loading {{
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                color: #fff;
                font-size: 16px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}

            /* 隐藏浮动按钮 */
            .floating-buttons,
            .fab,
            .add-button,
            .upload-button,
            [class*="float"],
            [class*="fab"],
            [id*="float"],
            [id*="fab"] {{
                display: none !important;
                visibility: hidden !important;
            }}
        </style>
    </head>
    <body>
        <div class="pdf-container">
            <div class="loading" id="loading">正在加载PDF...</div>
            <iframe class="pdf-viewer"
                    src="{pdf_url}"
                    title="{document.doc_name}"
                    onload="document.getElementById('loading').style.display='none'"
                    onerror="document.getElementById('loading').innerHTML='PDF加载失败'">
            </iframe>
        </div>

        <script>
            // 隐藏浮动按钮
            function hideFloatingButtons() {{
                const selectors = [
                    '.floating-buttons', '.fab', '.add-button', '.upload-button',
                    '[class*="float"]', '[class*="fab"]', '[id*="float"]', '[id*="fab"]'
                ];

                selectors.forEach(selector => {{
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {{
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                    }});
                }});

                try {{
                    if (window.parent && window.parent.document) {{
                        selectors.forEach(selector => {{
                            const elements = window.parent.document.querySelectorAll(selector);
                            elements.forEach(el => {{
                                el.style.display = 'none';
                                el.style.visibility = 'hidden';
                            }});
                        }});
                    }}
                }} catch(e) {{
                    // 跨域限制，忽略错误
                }}
            }}

            document.addEventListener('DOMContentLoaded', hideFloatingButtons);
            setInterval(hideFloatingButtons, 1000);
        </script>
    </body>
    </html>
    """
    return html_content
