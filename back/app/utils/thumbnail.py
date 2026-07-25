"""缩略图生成工具"""
import io
import logging
from PIL import Image

logger = logging.getLogger(__name__)

DEFAULT_SIZE = (200, 200)
DEFAULT_QUALITY = 85


def generate_thumbnail(
    image_bytes: bytes,
    size: tuple = DEFAULT_SIZE,
    quality: int = DEFAULT_QUALITY,
) -> bytes:
    """生成缩略图

    Args:
        image_bytes: 原始图片字节
        size: 缩略图最大尺寸 (width, height)，保持宽高比
        quality: JPEG 质量 (1-100)

    Returns:
        缩略图 JPEG 字节
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # 转换 RGBA 为 RGB（JPEG 不支持 alpha）
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        img.thumbnail(size, Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        return buffer.getvalue()
    except Exception as e:
        logger.error(f"生成缩略图失败: {e}")
        raise