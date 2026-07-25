#!/usr/bin/env python3
"""
图片转换器
将图片文件转换为HTML格式
"""

import os
import logging
from typing import Tuple, Optional

from .base import BaseConverter, HTMLWrapper, ConversionError

logger = logging.getLogger(__name__)


class ImageConverter(BaseConverter):
    """图片转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
    
    def is_supported(self, file_type: str) -> bool:
        """检查文件类型是否支持转换"""
        return file_type.lower() in self.supported_formats
    
    def convert_to_html(self, file_path: str, file_type: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """转换图片文件为HTML"""
        try:
            # 验证文件
            is_valid, error_msg = self.validate_file(file_path)
            if not is_valid:
                return False, None, error_msg

            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)

            # 获取图片的base64编码
            import base64
            with open(file_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # 确定MIME类型
            mime_types = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'gif': 'image/gif',
                'bmp': 'image/bmp',
                'webp': 'image/webp'
            }
            mime_type = mime_types.get(file_type.lower(), 'image/jpeg')

            # 创建简洁的图片预览HTML（适合在preview-content区域内显示）
            html_content = f"""
            <script>
                // 预先定义函数，避免onload时函数未定义的问题
                function handleImageLoad() {{
                    console.log('图片加载成功');
                }}

                function handleImageError() {{
                    console.error('图片加载失败');
                    const container = document.getElementById('imageContainer');
                    if (container) {{
                        container.innerHTML = `
                            <div class="error-message">
                                <div class="error-icon">😞</div>
                                <div class="error-text">图片加载失败</div>
                                <div class="error-hint">请检查网络连接或稍后重试</div>
                            </div>
                        `;
                    }}
                }}
            </script>
            <div class="simple-image-viewer">
                <div class="image-container" id="imageContainer">
                    <img src="data:{mime_type};base64,{image_data}"
                         alt="{HTMLWrapper.escape_html(file_name)}"
                         class="preview-image"
                         id="mainImage"
                         onload="handleImageLoad()"
                         onerror="handleImageError()">
                </div>
            </div>

            <script>
                // 页面初始化
                document.addEventListener('DOMContentLoaded', function() {{
                    const img = document.getElementById('mainImage');
                    const container = document.getElementById('imageContainer');

                    if (img && container) {{
                        // 防止默认的图片拖拽行为
                        img.addEventListener('dragstart', e => e.preventDefault());

                        // 防止右键菜单
                        img.addEventListener('contextmenu', e => e.preventDefault());

                        // 添加鼠标滚轮垂直滚动功能
                        container.addEventListener('wheel', function(e) {{
                            // 阻止默认的缩放行为
                            e.preventDefault();

                            // 计算滚动距离
                            const scrollAmount = e.deltaY * 0.5; // 调整滚动速度

                            // 执行垂直滚动
                            container.scrollTop += scrollAmount;
                        }}, {{ passive: false }});

                        // 确保容器可以获得焦点以接收滚轮事件
                        container.setAttribute('tabindex', '0');
                        container.style.outline = 'none';
                    }}
                }});
            </script>
            """

            full_html = self._wrap_image_html(html_content, f"图片预览 - {file_name}")
            return True, full_html, None

        except Exception as e:
            logger.error(f"转换图片失败: {str(e)}")
            return False, None, str(e)
    
    def _wrap_image_html(self, content: str, title: str) -> str:
        """为图片内容包装HTML页面"""
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
                    margin: 0;
                    padding: 0;
                    background: #f8f9fa;
                    color: #333;
                    font-size: 16px;
                    -webkit-text-size-adjust: 100%;
                    -webkit-font-smoothing: antialiased;
                }}

                .simple-image-viewer {{
                    width: 100%;
                    height: 100%;
                    min-height: 400px;
                    display: block;
                    background: #f8f9fa;
                    position: relative;
                }}

                .image-container {{
                    width: 100%;
                    height: 100%;
                    overflow-x: hidden;
                    overflow-y: auto;
                    -webkit-overflow-scrolling: touch;
                    position: relative;
                    padding: 0;
                    background: #fff;
                    box-sizing: border-box;
                }}

                .preview-image {{
                    width: 100%;
                    height: auto;
                    display: block;
                    object-fit: contain;
                    object-position: top center;
                    flex-shrink: 0;
                    user-select: none;
                    -webkit-user-select: none;
                    -webkit-touch-callout: none;
                    -webkit-user-drag: none;
                    -khtml-user-drag: none;
                    -moz-user-drag: none;
                    -o-user-drag: none;
                    user-drag: none;
                }}

                .preview-image:active {{
                    cursor: grabbing;
                }}

                .error-message {{
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                    color: #6c757d;
                    padding: 40px 20px;
                    height: 100%;
                }}

                .error-icon {{
                    font-size: 48px;
                    margin-bottom: 15px;
                }}

                .error-text {{
                    color: #dc3545;
                    font-size: 18px;
                    font-weight: 600;
                    margin-bottom: 10px;
                }}

                .error-hint {{
                    color: #6c757d;
                    font-size: 14px;
                    margin-bottom: 20px;
                }}

                /* 移动端优化 */
                @media (max-width: 768px) {{
                    .image-container {{
                        padding: 0;
                        min-height: 200px;
                    }}

                    .preview-image {{
                        width: 100%;
                    }}

                    .error-icon {{
                        font-size: 24px;
                    }}

                    .error-text {{
                        font-size: 16px;
                    }}

                    .error-hint {{
                        font-size: 13px;
                    }}
                }}

                /* 小屏幕优化 */
                @media (max-width: 480px) {{
                    .image-container {{
                        padding: 0;
                        min-height: 150px;
                    }}

                    .preview-image {{
                        width: 100%;
                    }}

                    .error-message {{
                        padding: 20px 10px;
                    }}

                    .error-icon {{
                        font-size: 32px;
                    }}

                    .error-text {{
                        font-size: 14px;
                    }}

                    .error-hint {{
                        font-size: 12px;
                    }}
                }}

                /* 滚动条样式 - 更明显的滚动条 */
                .image-container::-webkit-scrollbar {{
                    width: 12px;
                    height: 12px;
                }}

                .image-container::-webkit-scrollbar-track {{
                    background: #f1f3f4;
                    border-radius: 6px;
                    border: 1px solid #e8eaed;
                }}

                .image-container::-webkit-scrollbar-thumb {{
                    background: #c1c8cd;
                    border-radius: 6px;
                    border: 2px solid #f1f3f4;
                    min-height: 20px;
                }}

                .image-container::-webkit-scrollbar-thumb:hover {{
                    background: #9aa0a6;
                }}

                .image-container::-webkit-scrollbar-thumb:active {{
                    background: #5f6368;
                }}

                /* 滚动条在移动端的优化 */
                @media (max-width: 768px) {{
                    .image-container::-webkit-scrollbar {{
                        width: 4px;
                        height: 4px;
                    }}

                    .image-container::-webkit-scrollbar-thumb {{
                        background: rgba(0,0,0,0.2);
                        border: none;
                    }}

                    .image-container::-webkit-scrollbar-thumb:hover {{
                        background: rgba(0,0,0,0.3);
                    }}
                }}

                /* 防止图片被选中 */
                .preview-image {{
                    -webkit-user-drag: none;
                    -khtml-user-drag: none;
                    -moz-user-drag: none;
                    -o-user-drag: none;
                    user-drag: none;
                }}
            </style>
        </head>
        <body>
            {content}
        </body>
        </html>
        """
