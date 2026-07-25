#!/usr/bin/env python3
"""
PPT文件解析器
不依赖COM接口的PPT文件内容提取工具
"""

import os
import logging
import struct
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class PPTParser:
    """PPT文件解析器"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.slides_content = []
        
    def parse(self) -> bool:
        """解析PPT文件"""
        try:
            logger.info(f"开始解析PPT文件: {self.file_path}")
            
            # 方法1: 尝试使用olefile解析OLE结构
            if self._parse_with_olefile():
                return True
                
            # 方法2: 尝试简单的二进制解析
            if self._parse_binary_content():
                return True
                
            # 方法3: 尝试提取可见文本
            if self._extract_visible_text():
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"PPT解析失败: {str(e)}")
            return False
    
    def _parse_with_olefile(self) -> bool:
        """使用olefile解析OLE结构"""
        try:
            import olefile

            if not olefile.isOleFile(self.file_path):
                logger.info("不是有效的OLE文件")
                return False

            ole = olefile.OleFileIO(self.file_path)

            # 查找PowerPoint相关的流
            streams = ole.listdir()
            logger.info(f"找到OLE流: {streams}")

            # 尝试读取多种可能的PowerPoint流
            potential_streams = []
            for stream in streams:
                stream_name = str(stream).lower()
                if any(keyword in stream_name for keyword in ['powerpoint', 'document', 'current user', 'pictures']):
                    potential_streams.append(stream)

            if potential_streams:
                logger.info(f"找到潜在的PowerPoint流: {potential_streams}")

                for stream_name in potential_streams:
                    try:
                        stream = ole.openstream(stream_name)
                        data = stream.read()

                        # 尝试提取文本内容
                        text_content = self._extract_text_from_binary(data)
                        if text_content:
                            self.slides_content.append({
                                'slide_number': len(self.slides_content) + 1,
                                'title': f"从{stream_name}提取的内容",
                                'content': text_content
                            })

                    except Exception as stream_error:
                        logger.debug(f"读取流{stream_name}失败: {stream_error}")
                        continue

            # 如果没有找到特定流，尝试读取所有流
            if not self.slides_content:
                logger.info("尝试读取所有OLE流")
                for stream_name in streams:
                    try:
                        if len(stream_name) == 1 and isinstance(stream_name[0], str):
                            stream = ole.openstream(stream_name)
                            data = stream.read()

                            # 只处理包含文本的流
                            if len(data) > 100:  # 忽略太小的流
                                text_content = self._extract_text_from_binary(data)
                                if text_content and len(text_content) > 50:
                                    self.slides_content.append({
                                        'slide_number': len(self.slides_content) + 1,
                                        'title': f"从{stream_name[0]}流提取的内容",
                                        'content': text_content
                                    })

                                    # 限制提取的内容块数量
                                    if len(self.slides_content) >= 3:
                                        break

                    except Exception as stream_error:
                        logger.debug(f"读取流{stream_name}失败: {stream_error}")
                        continue

            ole.close()

            return len(self.slides_content) > 0
            
        except ImportError:
            logger.debug("olefile库未安装")
            return False
        except Exception as e:
            logger.debug(f"olefile解析失败: {str(e)}")
            return False
    
    def _parse_binary_content(self) -> bool:
        """简单的二进制内容解析"""
        try:
            with open(self.file_path, 'rb') as f:
                data = f.read()
            
            # 查找可能的文本内容
            text_content = self._extract_text_from_binary(data)
            
            if text_content:
                self.slides_content.append({
                    'slide_number': 1,
                    'title': "提取的文本内容",
                    'content': text_content
                })
                return True
                
            return False
            
        except Exception as e:
            logger.debug(f"二进制解析失败: {str(e)}")
            return False
    
    def _extract_visible_text(self) -> bool:
        """提取可见文本内容"""
        try:
            with open(self.file_path, 'rb') as f:
                data = f.read()
            
            # 尝试解码为文本，忽略错误
            try:
                text = data.decode('utf-8', errors='ignore')
            except:
                text = data.decode('latin-1', errors='ignore')
            
            # 过滤出可能的文本内容
            lines = []
            for line in text.split('\n'):
                line = line.strip()
                # 过滤掉二进制垃圾和太短的行
                if len(line) > 3 and self._is_likely_text(line):
                    lines.append(line)
            
            if lines:
                content = '\n'.join(lines[:50])  # 限制行数
                self.slides_content.append({
                    'slide_number': 1,
                    'title': "文本内容提取",
                    'content': content
                })
                return True
                
            return False
            
        except Exception as e:
            logger.debug(f"文本提取失败: {str(e)}")
            return False
    
    def _extract_text_from_binary(self, data: bytes) -> str:
        """从二进制数据中提取文本"""
        try:
            # 尝试多种编码
            encodings = ['utf-16le', 'utf-16be', 'utf-8', 'latin-1', 'cp1252', 'cp1251']

            best_text = ""
            best_score = 0

            for encoding in encodings:
                try:
                    text = data.decode(encoding, errors='ignore')

                    # 提取可能的文本行
                    lines = []
                    for line in text.split('\n'):
                        line = line.strip()
                        # 清理行内容
                        cleaned_line = self._clean_text_line(line)
                        if len(cleaned_line) > 3 and self._is_likely_text(cleaned_line):
                            lines.append(cleaned_line)

                    if len(lines) > 1:  # 至少要有几行有意义的文本
                        current_text = '\n'.join(lines[:50])  # 限制行数

                        # 计算文本质量分数
                        score = self._calculate_text_quality(current_text)
                        if score > best_score:
                            best_score = score
                            best_text = current_text

                except:
                    continue

            return best_text if best_score > 0 else ""

        except Exception as e:
            logger.debug(f"文本提取失败: {str(e)}")
            return ""

    def _clean_text_line(self, line: str) -> str:
        """清理文本行"""
        if not line:
            return ""

        # 移除控制字符
        cleaned = ''.join(char for char in line if ord(char) >= 32 or char in '\t\n')

        # 移除过多的空格
        cleaned = ' '.join(cleaned.split())

        return cleaned.strip()

    def _calculate_text_quality(self, text: str) -> int:
        """计算文本质量分数"""
        if not text:
            return 0

        score = 0
        lines = text.split('\n')

        # 基于行数评分
        score += min(len(lines), 10) * 2

        # 基于字符多样性评分
        unique_chars = len(set(text.lower()))
        score += min(unique_chars, 50)

        # 基于单词数量评分
        words = text.split()
        score += min(len(words), 100)

        # 检查是否包含常见的演示文稿关键词
        keywords = ['slide', 'presentation', 'title', 'content', '幻灯片', '演示', '标题', '内容']
        for keyword in keywords:
            if keyword.lower() in text.lower():
                score += 10

        return score
    
    def _is_likely_text(self, line: str) -> bool:
        """判断一行文本是否可能是有意义的内容"""
        if not line:
            return False
        
        # 过滤掉明显的二进制垃圾
        if len([c for c in line if ord(c) < 32 or ord(c) > 126]) > len(line) * 0.3:
            return False
        
        # 过滤掉全是特殊字符的行
        if all(not c.isalnum() for c in line):
            return False
        
        # 过滤掉太多重复字符的行
        if len(set(line)) < len(line) * 0.3:
            return False
        
        return True
    
    def get_slides_content(self) -> List[Dict[str, Any]]:
        """获取解析出的幻灯片内容"""
        return self.slides_content
    
    def has_content(self) -> bool:
        """检查是否有提取到内容"""
        return len(self.slides_content) > 0
