#!/usr/bin/env python3
"""
Office文档转换工具
将Office文档转换为HTML格式以便在浏览器中预览

重构说明：
- 将原来的单一大文件拆分为多个专门的转换器模块
- 每个转换器负责特定类型的文档转换
- 使用统一的接口和基类来保证一致性
- 主转换器类作为统一入口，协调各个专门的转换器
"""

import logging
from typing import Tuple, Optional

from .converters import (
    DocxConverter,
    XlsxConverter, 
    PptxConverter,
    PdfConverter,
    ImageConverter,
    LegacyConverter,
    ConversionError
)

logger = logging.getLogger(__name__)


class OfficeConverter:
    """Office文档转换器 - 统一入口"""
    
    def __init__(self):
        # 初始化各种专门的转换器
        self.docx_converter = DocxConverter()
        self.xlsx_converter = XlsxConverter()
        self.pptx_converter = PptxConverter()
        self.pdf_converter = PdfConverter()
        self.image_converter = ImageConverter()
        self.legacy_converter = LegacyConverter()
        
        # 构建支持的格式列表
        self.supported_formats = []
        for converter in [self.docx_converter, self.xlsx_converter, self.pptx_converter, 
                         self.pdf_converter, self.image_converter, self.legacy_converter]:
            self.supported_formats.extend(converter.supported_formats)
    
    def is_supported(self, file_type: str) -> bool:
        """检查文件类型是否支持转换"""
        return file_type.lower() in self.supported_formats
    
    def convert_to_html(self, file_path: str, file_type: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        将Office文档或PDF转换为HTML

        Args:
            file_path: 文件路径
            file_type: 文件类型

        Returns:
            tuple: (success, html_content, error_message)
        """
        try:
            file_type = file_type.lower()
            
            # 根据文件类型选择合适的转换器
            if self.docx_converter.is_supported(file_type):
                return self.docx_converter.convert_to_html(file_path, file_type)
            elif self.xlsx_converter.is_supported(file_type):
                return self.xlsx_converter.convert_to_html(file_path, file_type)
            elif self.pptx_converter.is_supported(file_type):
                return self.pptx_converter.convert_to_html(file_path, file_type)
            elif self.pdf_converter.is_supported(file_type):
                return self.pdf_converter.convert_to_html(file_path, file_type)
            elif self.image_converter.is_supported(file_type):
                return self.image_converter.convert_to_html(file_path, file_type)
            elif self.legacy_converter.is_supported(file_type):
                return self.legacy_converter.convert_to_html(file_path, file_type)
            else:
                return False, None, f"不支持的文件类型: {file_type}"

        except ConversionError as e:
            logger.error(f"转换错误: {str(e)}")
            return False, None, str(e)
        except Exception as e:
            logger.error(f"转换文档失败: {str(e)}")
            return False, None, f"转换失败: {str(e)}"


# 为了保持向后兼容性，保留一些常用的工具函数
def escape_html(text: str) -> str:
    """转义HTML特殊字符 - 向后兼容"""
    from .converters import HTMLWrapper
    return HTMLWrapper.escape_html(text)


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小 - 向后兼容"""
    from .converters import HTMLWrapper
    return HTMLWrapper.format_file_size(size_bytes)


# 全局转换器实例
office_converter = OfficeConverter()
