"""
知识库文件处理工具模块
包含文件验证、哈希计算、文件名编码、路径处理等工具函数
"""
import hashlib
import os
from urllib.parse import quote

from app.core.config import settings

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md',
                     'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'}


def allowed_file(filename):
    """
    检查文件是否为允许的类型
    
    Args:
        filename (str): 文件名
        
    Returns:
        bool: 是否为允许的文件类型
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_hash(file_path):
    """
    计算文件的MD5哈希值
    
    Args:
        file_path (str): 文件路径
        
    Returns:
        str: 文件的MD5哈希值
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def encode_filename_for_header(filename):
    """
    为HTTP头编码文件名，支持中文字符
    使用RFC 5987标准的filename*参数
    
    Args:
        filename (str): 原始文件名
        
    Returns:
        str: 编码后的文件名字符串
    """
    try:
        # 尝试ASCII编码
        filename.encode('ascii')
        return f'filename="{filename}"'
    except UnicodeEncodeError:
        # 包含非ASCII字符，使用RFC 5987编码
        encoded_filename = quote(filename, safe='')
        return f'filename*=UTF-8\'\'{encoded_filename}'


def format_file_size(size_bytes):
    """
    格式化文件大小显示
    
    Args:
        size_bytes (int): 文件大小（字节）
        
    Returns:
        str: 格式化后的文件大小字符串
    """
    if size_bytes > 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    elif size_bytes > 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes} B"


def get_file_extension(filename):
    """
    安全地获取文件扩展名
    
    Args:
        filename (str): 文件名
        
    Returns:
        str: 文件扩展名（小写）
    """
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


def is_image_file(file_ext):
    """
    判断是否为图片文件
    
    Args:
        file_ext (str): 文件扩展名
        
    Returns:
        bool: 是否为图片文件
    """
    return file_ext.lower() in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg']


def is_office_file(file_ext):
    """
    判断是否为Office文件
    
    Args:
        file_ext (str): 文件扩展名
        
    Returns:
        bool: 是否为Office文件
    """
    return file_ext.lower() in ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']


def is_pdf_file(file_ext):
    """
    判断是否为PDF文件
    
    Args:
        file_ext (str): 文件扩展名
        
    Returns:
        bool: 是否为PDF文件
    """
    return file_ext.lower() == 'pdf'


def is_text_file(file_ext):
    """
    判断是否为文本文件
    
    Args:
        file_ext (str): 文件扩展名
        
    Returns:
        bool: 是否为文本文件
    """
    return file_ext.lower() in ['txt', 'md', 'log']


def get_mime_type_by_extension(file_ext):
    """
    根据文件扩展名获取MIME类型
    
    Args:
        file_ext (str): 文件扩展名
        
    Returns:
        str: MIME类型
    """
    mime_types = {
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'ppt': 'application/vnd.ms-powerpoint',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'txt': 'text/plain',
        'md': 'text/markdown',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'bmp': 'image/bmp',
        'webp': 'image/webp',
        'svg': 'image/svg+xml'
    }
    return mime_types.get(file_ext.lower(), 'application/octet-stream')


def get_full_path(relative_path: str) -> str:
    """拼接存储根目录和相对路径

    Args:
        relative_path: 相对于 STORAGE_PATH 的路径

    Returns:
        完整的绝对路径

    Raises:
        ValueError: 路径包含非法字符（如 ..）
    """
    if not relative_path or '..' in relative_path or relative_path.startswith(('/', '\\')):
        raise ValueError(f"非法相对路径: {relative_path}")
    # 统一路径分隔符：数据库中可能残留 Windows 反斜杠，在 Linux 环境下会导致路径不存在
    normalized = relative_path.replace("\\", "/")
    storage_root = str(settings.STORAGE_PATH_RESOLVED)
    return os.path.join(storage_root, normalized)
