#!/usr/bin/env python3
"""
文档转换器基础接口和工具类
定义统一的转换器接口，提供通用的工具方法
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class BaseConverter(ABC):
    """文档转换器基类"""
    
    def __init__(self):
        self.supported_formats = []
    
    @abstractmethod
    def is_supported(self, file_type: str) -> bool:
        """检查文件类型是否支持转换"""
        pass
    
    @abstractmethod
    def convert_to_html(self, file_path: str, file_type: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        将文档转换为HTML
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
            
        Returns:
            tuple: (success, html_content, error_message)
        """
        pass
    
    def validate_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """验证文件是否存在且可读"""
        if not os.path.exists(file_path):
            return False, "文件不存在"
        
        if not os.path.isfile(file_path):
            return False, "路径不是文件"
        
        if not os.access(file_path, os.R_OK):
            return False, "文件无法读取"
        
        return True, None


class HTMLWrapper:
    """HTML包装器工具类"""
    
    @staticmethod
    def escape_html(text: str) -> str:
        """转义HTML特殊字符"""
        if not text:
            return ""
        
        text = str(text)
        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;'
        }
        
        for char, escaped in replacements.items():
            text = text.replace(char, escaped)
        
        return text
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    @staticmethod
    def get_column_letter(col_num: int) -> str:
        """将列号转换为Excel列字母（1->A, 2->B, ...）"""
        result = ""
        while col_num > 0:
            col_num -= 1
            result = chr(col_num % 26 + ord('A')) + result
            col_num //= 26
        return result
    
    @staticmethod
    def wrap_basic_html(content: str, title: str) -> str:
        """包装基础HTML内容为完整页面"""
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
                    line-height: 1.5;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 5px;
                    background: white;
                    color: #333;
                    font-size: 14px;
                    -webkit-text-size-adjust: 100%;
                    -webkit-font-smoothing: antialiased;
                }}
                .container {{
                    background: white;
                    padding: 8px;
                    margin: 0;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: #2c3e50;
                    margin: 15px 0 8px 0;
                    word-wrap: break-word;
                }}
                p {{
                    margin: 8px 0;
                    word-wrap: break-word;
                    line-height: 1.5;
                    font-size: 14px;
                }}
                /* 移动端优化 */
                @media (max-width: 768px) {{
                    body {{
                        padding: 3px;
                        font-size: 13px;
                    }}
                    .container {{
                        padding: 6px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="content">
                    {content}
                </div>
            </div>
        </body>
        </html>
        """


class ConversionError(Exception):
    """转换错误异常类"""
    
    def __init__(self, message: str, file_path: str = None, file_type: str = None):
        super().__init__(message)
        self.file_path = file_path
        self.file_type = file_type
        self.message = message
    
    def __str__(self):
        if self.file_path and self.file_type:
            return f"转换{self.file_type}文件失败 ({self.file_path}): {self.message}"
        return f"转换失败: {self.message}"
