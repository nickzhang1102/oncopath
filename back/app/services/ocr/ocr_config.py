"""OCR服务配置"""
import re

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OCRConfig(BaseSettings):
    """OCR配置类"""

    # PaddleOCR配置
    # 方向分类器在CPU+MKLDNN环境下存在跨线程推理bug (PaddleOCR #15621)
    # Docker环境必须禁用，避免RuntimeError: std::exception
    paddle_use_angle_cls: bool = False
    paddle_lang: str = 'ch'
    paddle_device: str = 'cpu'
    paddle_show_log: bool = False

    # 表格识别配置（检验类报告）
    use_table_recognition: bool = True

    # 图像预处理配置
    image_min_width: int = 100
    image_min_height: int = 100
    image_max_size: int = 12000  # 支持长条形报告图片
    image_max_width: int = 4096  # 最大宽度
    image_max_height: int = 12000  # 最大高度，支持长报告
    image_ocr_max_dimension: int = 4000  # OCR前预缩放最大边长，防止大图OOM

    # 文本提取配置
    min_text_confidence: float = 0.5
    max_text_length: int = 200

    # OCR 重试配置（首次识别为空时启用）
    retry_resize_scale: float = 1.5  # 重试前图片放大倍数
    retry_clahe_clip_limit: float = 2.0  # CLAHE 对比度限制
    retry_clahe_tile_size: int = 8  # CLAHE 网格尺寸
    retry_threshold_block_size: int = 31  # 自适应阈值块大小
    retry_threshold_c: int = 11  # 自适应阈值常数

    # 分段识别配置（长图裁剪后）
    segment_step: int = 1400  # 分段步长
    segment_overlap: int = 180  # 分段重叠
    segment_min_height: int = 1800  # 低于此高度不做分段

    # 内容区域裁剪配置
    crop_padding: int = 24  # 裁剪边距
    crop_min_area_ratio: float = 0.98  # 裁剪后面积 >= 原面积 * 此比例时不裁剪

    @field_validator("paddle_device")
    @classmethod
    def validate_paddle_device(cls, value: str) -> str:
        """只接受 PaddleOCR 支持的本地 CPU/GPU 设备格式。"""
        device = value.strip().lower()
        if device == "cpu" or re.fullmatch(r"gpu(?::\d+)?", device):
            return device
        raise ValueError("OCR_PADDLE_DEVICE 仅支持 cpu、gpu 或 gpu:<非负设备序号>")

    model_config = SettingsConfigDict(
        env_prefix="OCR_",
        case_sensitive=False
    )


# 全局配置实例
ocr_config = OCRConfig()
