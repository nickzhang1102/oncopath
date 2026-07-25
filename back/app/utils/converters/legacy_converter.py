#!/usr/bin/env python3
"""
旧格式文档转换器
将DOC/XLS/PPT等旧格式文档转换为HTML格式

转换方案：
- .doc → COM/olefile/textract 降级链
- .xls → xlrd 库
- .ppt → markitdown (olefile) + PPTParser 降级链
"""

import os
import logging
from typing import Tuple, Optional

from .base import BaseConverter, HTMLWrapper, ConversionError

logger = logging.getLogger(__name__)


class LegacyConverter(BaseConverter):
    """旧格式文档转换器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['doc', 'xls', 'ppt']
    
    def is_supported(self, file_type: str) -> bool:
        """检查文件类型是否支持转换"""
        return file_type.lower() in self.supported_formats
    
    def convert_to_html(self, file_path: str, file_type: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """转换旧格式文档为HTML"""
        try:
            # 验证文件
            is_valid, error_msg = self.validate_file(file_path)
            if not is_valid:
                return False, None, error_msg
            
            file_type = file_type.lower()
            
            if file_type == 'doc':
                return self._convert_doc_to_html(file_path)
            elif file_type == 'xls':
                return self._convert_xls_to_html(file_path)
            elif file_type == 'ppt':
                return self._convert_ppt_to_html(file_path)
            else:
                return False, None, f"不支持的文件类型: {file_type}"
                
        except Exception as e:
            logger.error(f"转换旧格式文档失败: {str(e)}")
            return False, None, str(e)
    
    def _convert_doc_to_html(self, file_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """转换DOC文档为HTML"""
        try:
            # 方法1: 尝试使用Windows COM接口调用Microsoft Word
            html_content = self._convert_doc_with_word_com(file_path)
            if html_content:
                full_html = HTMLWrapper.wrap_basic_html(html_content, "Word文档预览")
                return True, full_html, None

            # 方法2: 尝试使用olefile解析.doc文件结构
            html_content = self._convert_doc_with_olefile(file_path)
            if html_content:
                full_html = HTMLWrapper.wrap_basic_html(html_content, "Word文档预览")
                return True, full_html, None

            # 方法3: 尝试使用textract库
            try:
                import textract
                text_content = textract.process(file_path).decode('utf-8')
                if text_content:
                    # 将文本转换为HTML段落，保持基本格式
                    html_content = self._text_to_html(text_content)
                    if html_content:
                        full_html = HTMLWrapper.wrap_basic_html(html_content, "Word文档预览")
                        return True, full_html, None
            except ImportError:
                logger.debug("textract库未安装")
            except Exception as e:
                logger.warning(f"textract处理失败: {str(e)}")

            # 方法4: 如果以上方法都失败，返回基础信息
            file_size = os.path.getsize(file_path)
            basic_info = f"""
            <div style="text-align: center; padding: 40px;">
                <h2>📄 Word文档 (.doc)</h2>
                <p>文件大小: {HTMLWrapper.format_file_size(file_size)}</p>
                <p>旧版Word文档格式，无法直接预览内容。</p>
                <p>建议下载后使用Word或其他兼容软件打开。</p>
                <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 4px;">
                    <p><strong>提示：</strong>为了获得更好的预览效果，建议：</p>
                    <ul style="text-align: left; display: inline-block;">
                        <li>将.doc文件转换为.docx格式</li>
                        <li>安装Microsoft Word或LibreOffice</li>
                        <li>使用在线文档转换工具</li>
                    </ul>
                </div>
            </div>
            """
            full_html = HTMLWrapper.wrap_basic_html(basic_info, "Word文档预览")
            return True, full_html, None

        except Exception as e:
            logger.error(f"转换DOC失败: {str(e)}")
            return False, None, str(e)
    
    def _convert_xls_to_html(self, file_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """转换XLS文档为HTML，优化移动端显示"""
        try:
            # 尝试使用xlrd库
            try:
                import xlrd
                workbook = xlrd.open_workbook(file_path)
                content_parts = []

                for sheet_name in workbook.sheet_names():
                    sheet = workbook.sheet_by_name(sheet_name)
                    if sheet.nrows > 0:
                        max_rows = min(sheet.nrows, 100)
                        max_cols = min(sheet.ncols, 15)  # 移动端限制为15列

                        content_parts.append(f"<div class='excel-sheet'>")
                        content_parts.append(f"<h3 class='sheet-title'>📊 {HTMLWrapper.escape_html(sheet_name)}</h3>")

                        # 添加表格信息
                        content_parts.append(f"<div class='sheet-info'>")
                        content_parts.append(f"<span class='info-item'>📏 {sheet.nrows} 行 × {sheet.ncols} 列</span>")
                        if sheet.nrows > 100:
                            content_parts.append(f"<span class='info-item'>⚠️ 仅显示前100行</span>")
                        if sheet.ncols > 15:
                            content_parts.append(f"<span class='info-item'>⚠️ 仅显示前15列</span>")
                        content_parts.append(f"</div>")

                        # 创建移动端优化的表格
                        content_parts.append("<div class='excel-table-wrapper'>")
                        content_parts.append("<table class='excel-table'>")

                        # 添加列标题（A, B, C...）
                        content_parts.append("<thead><tr><th class='row-header'>#</th>")
                        for col_idx in range(max_cols):
                            col_letter = HTMLWrapper.get_column_letter(col_idx + 1)
                            content_parts.append(f"<th class='col-header'>{col_letter}</th>")
                        content_parts.append("</tr></thead>")

                        content_parts.append("<tbody>")
                        for row_idx in range(max_rows):
                            content_parts.append("<tr>")
                            # 行号
                            content_parts.append(f"<td class='row-header'>{row_idx + 1}</td>")

                            for col_idx in range(max_cols):
                                cell_value = str(sheet.cell_value(row_idx, col_idx))
                                # 截断过长的内容
                                if len(cell_value) > 50:
                                    display_value = cell_value[:47] + "..."
                                    content_parts.append(f"<td class='excel-cell' title='{HTMLWrapper.escape_html(cell_value)}'>{HTMLWrapper.escape_html(display_value)}</td>")
                                else:
                                    content_parts.append(f"<td class='excel-cell'>{HTMLWrapper.escape_html(cell_value)}</td>")
                            content_parts.append("</tr>")

                        content_parts.append("</tbody></table>")
                        content_parts.append("</div>")  # excel-table-wrapper
                        content_parts.append("</div>")  # excel-sheet

                if content_parts:
                    html_content = "\n".join(content_parts)
                    # 这里需要使用专门的Excel HTML包装器，但为了简化，先使用基础包装器
                    full_html = HTMLWrapper.wrap_basic_html(html_content, "Excel文档预览")
                    return True, full_html, None

            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"xlrd处理失败: {str(e)}")

            # 如果以上方法都失败，返回基础信息
            file_size = os.path.getsize(file_path)
            basic_info = f"""
            <div style="text-align: center; padding: 40px;">
                <h2>📊 Excel文档 (.xls)</h2>
                <p>文件大小: {HTMLWrapper.format_file_size(file_size)}</p>
                <p>旧版Excel文档格式，无法直接预览内容。</p>
                <p>建议下载后使用Excel或其他兼容软件打开。</p>
                <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 4px;">
                    <p><strong>提示：</strong>为了获得更好的预览效果，建议：</p>
                    <ul style="text-align: left; display: inline-block;">
                        <li>将.xls文件转换为.xlsx格式</li>
                        <li>安装Microsoft Excel或LibreOffice</li>
                        <li>使用在线文档转换工具</li>
                    </ul>
                </div>
            </div>
            """
            full_html = HTMLWrapper.wrap_basic_html(basic_info, "Excel文档预览")
            return True, full_html, None

        except Exception as e:
            logger.error(f"转换XLS失败: {str(e)}")
            return False, None, str(e)
    
    def _convert_ppt_to_html(self, file_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """转换PPT文档为HTML（使用 markitdown + olefile）"""
        logger.info(f"开始转换PPT文档: {file_path}")

        try:
            # 方法1: 使用 markitdown 转换（支持 .ppt 二进制格式，内部依赖 olefile）
            logger.info("尝试 markitdown 转换")
            html_content = self._convert_ppt_with_markitdown(file_path)
            if html_content:
                logger.info("markitdown 转换成功")
                full_html = HTMLWrapper.wrap_basic_html(html_content, "PowerPoint演示文稿")
                return True, full_html, None

            # 方法2: 使用 olefile 直接解析 OLE 结构
            logger.info("尝试 olefile 直接解析")
            html_content = self._convert_ppt_with_parser(file_path)
            if html_content:
                logger.info("olefile 解析成功")
                full_html = self._wrap_ppt_html(html_content, "PowerPoint演示文稿")
                return True, full_html, None

            # 所有方法失败，返回文件信息页
            logger.warning("所有转换方法都失败，生成信息页面")
            file_size = os.path.getsize(file_path)
            is_valid_ppt = self._validate_ppt_file(file_path)

            info_content = f"""
            <div class='presentation-overview'>
                <h1 class='presentation-title'>PowerPoint演示文稿</h1>
                <div class='presentation-info'>文件大小: {HTMLWrapper.format_file_size(file_size)}</div>
            </div>
            <div class='slide-container' data-slide='1'>
                <div class='slide-header'>
                    <h2 class='slide-title'>文档信息</h2>
                </div>
                <div class='slide-content'>
                    <p class='slide-text'><strong>文件格式：</strong>{"有效的PPT文件" if is_valid_ppt else "文件格式可能有问题"}</p>
                    <p class='slide-text'>旧版PPT格式(.ppt)内容提取受限，建议将文件转换为.pptx格式后重新上传以获得更好的预览效果。</p>
                </div>
            </div>
            """

            full_html = self._wrap_ppt_html(info_content, "PowerPoint演示文稿")
            return True, full_html, None

        except Exception as e:
            logger.error(f"转换PPT失败: {str(e)}")
            return False, None, str(e)

    def _validate_ppt_file(self, file_path: str) -> bool:
        """验证PPT文件格式"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8)
                if header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
                    return True
                if header.startswith(b'PK\x03\x04'):
                    return True
                return False
        except Exception:
            return False

    def _convert_ppt_with_markitdown(self, file_path: str) -> Optional[str]:
        """使用 markitdown 转换 PPT 文件为 HTML（markitdown 内部使用 olefile 解析 OLE 结构）"""
        try:
            from markitdown import MarkItDown
            import markdown as md_lib

            md_converter = MarkItDown()
            result = md_converter.convert(file_path)

            if not result or not result.text_content or not result.text_content.strip():
                logger.info("markitdown 未提取到有效内容")
                return None

            md_text = result.text_content.strip()
            logger.info(f"markitdown 成功提取文本，长度: {len(md_text)}")

            # Markdown → HTML
            html_body = md_lib.markdown(
                md_text,
                extensions=['tables', 'fenced_code', 'nl2br']
            )

            return html_body

        except ImportError as e:
            logger.warning(f"markitdown 依赖缺失: {e}")
            return None
        except Exception as e:
            logger.warning(f"markitdown 转换失败: {e}")
            return None

    def _convert_doc_with_word_com(self, file_path: str) -> Optional[str]:
        """使用Windows COM接口调用Microsoft Word转换.doc文件"""
        try:
            import win32com.client

            # 创建Word应用程序对象
            word_app = win32com.client.Dispatch("Word.Application")
            word_app.Visible = False
            word_app.DisplayAlerts = False

            # 打开文档
            doc = word_app.Documents.Open(file_path)

            # 获取文档内容
            content_parts = []

            # 提取段落
            for paragraph in doc.Paragraphs:
                text = paragraph.Range.Text.strip()
                if text:
                    content_parts.append(f"<p>{HTMLWrapper.escape_html(text)}</p>")

            # 提取表格
            for table in doc.Tables:
                content_parts.append("<table border='1' style='border-collapse: collapse; width: 100%;'>")
                for row in table.Rows:
                    content_parts.append("<tr>")
                    for cell in row.Cells:
                        cell_text = cell.Range.Text.strip()
                        content_parts.append(f"<td style='padding: 8px; border: 1px solid #ddd;'>{HTMLWrapper.escape_html(cell_text)}</td>")
                    content_parts.append("</tr>")
                content_parts.append("</table><br>")

            # 关闭文档和应用程序
            doc.Close()
            word_app.Quit()

            return "\n".join(content_parts) if content_parts else None

        except Exception as e:
            logger.warning(f"Word COM转换失败: {str(e)}")
            return None

    def _convert_doc_with_olefile(self, file_path: str) -> Optional[str]:
        """使用olefile解析.doc文件结构"""
        try:
            import olefile

            if not olefile.isOleFile(file_path):
                return None

            ole = olefile.OleFileIO(file_path)

            # 尝试提取文本内容
            # 这是一个简化的实现，实际的.doc格式非常复杂
            if ole.exists('WordDocument'):
                word_stream = ole.openstream('WordDocument')
                # 这里需要复杂的解析逻辑，简化处理
                content = word_stream.read()
                ole.close()

                # 简单的文本提取（不完整）
                text_content = content.decode('utf-8', errors='ignore')
                if text_content:
                    return self._text_to_html(text_content)

            ole.close()
            return None

        except Exception as e:
            logger.warning(f"olefile解析失败: {str(e)}")
            return None

    def _text_to_html(self, text_content: str) -> str:
        """将纯文本转换为格式化的HTML"""
        if not text_content:
            return ""

        lines = text_content.split('\n')
        html_parts = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 简单判断是否为标题
            if self._is_likely_title(line):
                html_parts.append(f"<h3>{HTMLWrapper.escape_html(line)}</h3>")
            else:
                html_parts.append(f"<p>{HTMLWrapper.escape_html(line)}</p>")

        return "\n".join(html_parts)

    def _is_likely_title(self, line: str) -> bool:
        """判断一行文本是否可能是标题"""
        if not line:
            return False

        # 简单的标题判断规则
        if len(line) < 100 and (
            line.isupper() or  # 全大写
            line.endswith(':') or  # 以冒号结尾
            any(keyword in line.lower() for keyword in ['第', '章', '节', '部分', 'chapter', 'section'])
        ):
            return True

        return False

    def _convert_ppt_with_parser(self, file_path: str) -> Optional[str]:
        """使用专门的PPT解析器提取内容"""
        try:
            from .ppt_parser import PPTParser

            logger.info(f"使用PPT解析器解析文件: {file_path}")
            parser = PPTParser(file_path)

            if parser.parse():
                slides_content = parser.get_slides_content()
                logger.info(f"PPT解析器成功提取{len(slides_content)}个内容块")

                content_parts = []

                # 添加演示文稿概览
                content_parts.append(f"<div class='presentation-overview'>")
                content_parts.append(f"<h1 class='presentation-title'>📽️ PowerPoint演示文稿</h1>")
                content_parts.append(f"<div class='presentation-info'>内容解析成功</div>")
                content_parts.append(f"</div>")

                # 处理每个内容块
                for i, slide_data in enumerate(slides_content, 1):
                    content_parts.append(f"<div class='slide-container' data-slide='{i}'>")
                    content_parts.append(f"<div class='slide-header'>")
                    content_parts.append(f"<h2 class='slide-title'>{HTMLWrapper.escape_html(slide_data.get('title', f'内容块 {i}'))}</h2>")
                    content_parts.append(f"<div class='slide-number'>第 {i} 部分</div>")
                    content_parts.append(f"</div>")
                    content_parts.append("<div class='slide-content'>")

                    # 处理内容
                    content = slide_data.get('content', '')
                    if content:
                        # 按段落分割
                        paragraphs = content.split('\n\n')
                        for paragraph in paragraphs:
                            paragraph = paragraph.strip()
                            if paragraph:
                                # 按行分割
                                lines = paragraph.split('\n')
                                for line in lines:
                                    line = line.strip()
                                    if line:
                                        if len(line) < 100 and not line.endswith('.'):
                                            # 可能是标题
                                            content_parts.append(f"<h3 class='slide-text-title'>{HTMLWrapper.escape_html(line)}</h3>")
                                        else:
                                            # 普通文本
                                            content_parts.append(f"<p class='slide-text'>{HTMLWrapper.escape_html(line)}</p>")
                    else:
                        content_parts.append("<p class='slide-text'>未能提取到文本内容</p>")

                    content_parts.append("</div></div>")

                return "\n".join(content_parts) if content_parts else None
            else:
                logger.info("PPT解析器未能提取到内容")
                return None

        except ImportError as import_error:
            logger.debug(f"PPT解析器导入失败: {import_error}")
            return None
        except Exception as e:
            logger.debug(f"PPT解析器转换失败: {str(e)}")
            return None

    def _wrap_ppt_html(self, content: str, title: str) -> str:
        """为PPT内容包装HTML页面，使用与PPTX相同的样式"""
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
                    margin: 0;
                    padding: 5px;
                    background: #f5f5f5;
                    color: #333;
                    font-size: 14px;
                    -webkit-text-size-adjust: 100%;
                    -webkit-font-smoothing: antialiased;
                }}

                .presentation-overview {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    margin-bottom: 20px;
                    border-radius: 8px;
                    text-align: center;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                }}

                .presentation-title {{
                    margin: 0 0 10px 0;
                    font-size: 24px;
                    font-weight: 700;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.3);
                }}

                .presentation-info {{
                    font-size: 16px;
                    opacity: 0.9;
                }}

                .slide-container {{
                    background: white;
                    margin-bottom: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    overflow: hidden;
                    page-break-after: always;
                }}

                .slide-header {{
                    background: linear-gradient(135deg, #ff6b35, #f7931e);
                    color: white;
                    padding: 15px 20px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}

                .slide-title {{
                    margin: 0;
                    font-size: 18px;
                    font-weight: 600;
                    text-shadow: 0 1px 2px rgba(0,0,0,0.1);
                }}

                .slide-number {{
                    font-size: 12px;
                    opacity: 0.9;
                    background: rgba(255,255,255,0.2);
                    padding: 4px 8px;
                    border-radius: 12px;
                }}

                .slide-content {{
                    padding: 25px;
                    min-height: 200px;
                    background: white;
                }}

                .slide-text-title {{
                    color: #2c3e50;
                    font-size: 22px;
                    font-weight: 700;
                    margin: 0 0 20px 0;
                    padding-bottom: 10px;
                    border-bottom: 3px solid #3498db;
                    position: relative;
                }}

                .slide-text-title::after {{
                    content: '';
                    position: absolute;
                    bottom: -3px;
                    left: 0;
                    width: 50px;
                    height: 3px;
                    background: #e74c3c;
                }}

                .slide-text {{
                    margin: 15px 0;
                    line-height: 1.8;
                    font-size: 16px;
                    color: #444;
                    text-align: justify;
                }}

                .slide-list {{
                    margin: 15px 0;
                    padding-left: 0;
                    list-style: none;
                }}

                .slide-list-item {{
                    margin: 8px 0;
                    padding: 8px 0 8px 20px;
                    position: relative;
                    font-size: 15px;
                    line-height: 1.6;
                }}

                .slide-list-item::before {{
                    content: '▶';
                    position: absolute;
                    left: 0;
                    color: #3498db;
                    font-weight: bold;
                }}

                .slide-table-container {{
                    margin: 20px 0;
                    overflow-x: auto;
                    border-radius: 6px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}

                .slide-table {{
                    width: 100%;
                    border-collapse: collapse;
                    background: white;
                }}

                .slide-table-cell {{
                    padding: 12px 15px;
                    border: 1px solid #e0e0e0;
                    text-align: left;
                    vertical-align: top;
                    font-size: 14px;
                }}

                .slide-table tr:first-child .slide-table-cell {{
                    background: #f8f9fa;
                    font-weight: 600;
                    color: #495057;
                }}

                .slide-table tr:nth-child(even) .slide-table-cell {{
                    background: #fdfdfe;
                }}

                .slide-image-placeholder {{
                    margin: 20px 0;
                    padding: 30px;
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    border-radius: 8px;
                    text-align: center;
                    color: white;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                }}

                .image-icon {{
                    font-size: 48px;
                    margin-bottom: 10px;
                }}

                .image-info {{
                    font-size: 16px;
                    font-weight: 600;
                    margin-bottom: 5px;
                }}

                .image-size {{
                    font-size: 14px;
                    opacity: 0.9;
                }}

                .no-content {{
                    text-align: center;
                    color: #6c757d;
                    font-style: italic;
                    padding: 40px 20px;
                    background: #f8f9fa;
                    border-radius: 4px;
                    border: 2px dashed #dee2e6;
                }}

                /* PPT转换状态页面样式 */
                .ppt-conversion-status {{
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}

                .status-header {{
                    text-align: center;
                    margin-bottom: 30px;
                    padding: 20px;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}

                .status-header h2 {{
                    margin: 0 0 10px 0;
                    color: #2c3e50;
                    font-size: 24px;
                }}

                .file-info {{
                    color: #666;
                    font-size: 14px;
                }}

                .conversion-attempts {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                }}

                .conversion-attempts h3 {{
                    margin: 0 0 15px 0;
                    color: #2c3e50;
                    font-size: 18px;
                }}

                .attempt-list {{
                    list-style: none;
                    padding: 0;
                    margin: 0;
                }}

                .attempt-item {{
                    display: flex;
                    align-items: center;
                    padding: 10px 0;
                    border-bottom: 1px solid #eee;
                }}

                .attempt-item:last-child {{
                    border-bottom: none;
                }}

                .attempt-icon {{
                    margin-right: 10px;
                    font-size: 16px;
                }}

                .attempt-text {{
                    color: #666;
                    font-size: 14px;
                }}

                .suggestions {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}

                .suggestions h3 {{
                    margin: 0 0 15px 0;
                    color: #2c3e50;
                    font-size: 18px;
                }}

                .suggestion-list {{
                    list-style: none;
                    padding: 0;
                    margin: 0;
                }}

                .suggestion-item {{
                    display: flex;
                    align-items: flex-start;
                    padding: 15px 0;
                    border-bottom: 1px solid #eee;
                }}

                .suggestion-item:last-child {{
                    border-bottom: none;
                }}

                .suggestion-icon {{
                    margin-right: 15px;
                    font-size: 20px;
                    margin-top: 2px;
                }}

                .suggestion-content strong {{
                    display: block;
                    color: #2c3e50;
                    font-size: 16px;
                    margin-bottom: 5px;
                }}

                .suggestion-content p {{
                    margin: 0;
                    color: #666;
                    font-size: 14px;
                    line-height: 1.5;
                }}

                /* 建议卡片样式 */
                .file-info-section,
                .conversion-status-section,
                .suggestions-section {{
                    margin: 20px 0;
                }}

                .suggestion-cards {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 15px;
                    margin-top: 15px;
                }}

                .suggestion-card {{
                    flex: 1;
                    min-width: 200px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                }}

                .suggestion-card .suggestion-icon {{
                    font-size: 32px;
                    margin-bottom: 10px;
                    display: block;
                }}

                .suggestion-card .suggestion-text {{
                    font-size: 14px;
                    line-height: 1.4;
                }}

                .suggestion-card .suggestion-text strong {{
                    display: block;
                    margin-bottom: 5px;
                    font-size: 16px;
                }}

                /* 移动端优化 */
                @media (max-width: 768px) {{
                    body {{
                        padding: 3px;
                        font-size: 13px;
                    }}

                    .slide-container {{
                        margin-bottom: 15px;
                        border-radius: 6px;
                    }}

                    .slide-header {{
                        padding: 12px 15px;
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 8px;
                    }}

                    .slide-title {{
                        font-size: 16px;
                    }}

                    .slide-number {{
                        font-size: 11px;
                        align-self: flex-end;
                    }}

                    .slide-content {{
                        padding: 20px 15px;
                        min-height: 150px;
                    }}

                    .slide-text-title {{
                        font-size: 18px;
                        margin-bottom: 12px;
                    }}

                    .slide-text {{
                        font-size: 14px;
                        margin: 10px 0;
                    }}

                    .ppt-conversion-status {{
                        padding: 10px;
                    }}

                    .status-header {{
                        padding: 15px;
                    }}

                    .conversion-attempts,
                    .suggestions {{
                        padding: 15px;
                    }}

                    .suggestion-cards {{
                        flex-direction: column;
                    }}

                    .suggestion-card {{
                        min-width: auto;
                    }}
                }}
            </style>
        </head>
        <body>
            {content}

            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    console.log('PowerPoint预览页面加载完成');

                    // 添加幻灯片导航功能
                    const slides = document.querySelectorAll('.slide-container');
                    console.log(`共找到 ${{slides.length}} 张幻灯片`);

                    // 键盘导航支持
                    document.addEventListener('keydown', function(e) {{
                        if (e.key === 'ArrowDown' || e.key === 'PageDown') {{
                            window.scrollBy(0, window.innerHeight * 0.8);
                            e.preventDefault();
                        }} else if (e.key === 'ArrowUp' || e.key === 'PageUp') {{
                            window.scrollBy(0, -window.innerHeight * 0.8);
                            e.preventDefault();
                        }}
                    }});
                }});
            </script>
        </body>
        </html>
        """
