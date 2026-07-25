"""图像预处理模块

提供图像增强、去噪、矫正等预处理功能
"""
import cv2
import numpy as np
from typing import Tuple, Optional
from pathlib import Path

from .ocr_config import ocr_config


class ImageProcessor:
    """图像预处理器"""

    @staticmethod
    def load_image(image_path: str) -> np.ndarray:
        """加载图片

        Args:
            image_path: 图片路径

        Returns:
            图片数组

        Raises:
            FileNotFoundError: 图片不存在
            ValueError: 图片格式不支持
        """
        if not Path(image_path).exists():
            raise FileNotFoundError(f"图片不存在: {image_path}")

        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法加载图片: {image_path}")

        return image

    @staticmethod
    def resize_image(
        image: np.ndarray,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None
    ) -> np.ndarray:
        """调整图片大小

        Args:
            image: 图片数组
            max_width: 最大宽度
            max_height: 最大高度

        Returns:
            调整后的图片
        """
        max_width = max_width or ocr_config.image_max_size
        max_height = max_height or ocr_config.image_max_size

        height, width = image.shape[:2]

        # 计算缩放比例
        scale = min(max_width / width, max_height / height)

        if scale < 1.0:
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

        return image

    @staticmethod
    def denoise_image(image: np.ndarray) -> np.ndarray:
        """去噪处理

        Args:
            image: 图片数组

        Returns:
            去噪后的图片
        """
        # 高斯滤波去噪
        denoised = cv2.GaussianBlur(image, (3, 3), 0)
        return denoised

    @staticmethod
    def enhance_contrast(image: np.ndarray) -> np.ndarray:
        """增强对比度（CLAHE）

        Args:
            image: 图片数组

        Returns:
            增强后的图片
        """
        # 转换到LAB颜色空间
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        # 分离通道
        l, a, b = cv2.split(lab)

        # 对L通道应用CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)

        # 合并通道
        lab_enhanced = cv2.merge([l_enhanced, a, b])

        # 转换回BGR
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

        return enhanced

    @staticmethod
    def binarize_image(image: np.ndarray) -> np.ndarray:
        """二值化处理

        Args:
            image: 图片数组

        Returns:
            二值化图片
        """
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 自适应阈值二值化
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )

        return binary

    @staticmethod
    def correct_skew(image: np.ndarray) -> Tuple[np.ndarray, float]:
        """矫正图片倾斜

        Args:
            image: 图片数组

        Returns:
            (矫正后的图片, 倾斜角度)
        """
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 边缘检测
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # 霍夫变换检测直线
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)

        if lines is None:
            return image, 0.0

        # 计算倾斜角度
        angles = []
        for line in lines:
            rho, theta = line[0]
            angle = np.degrees(theta) - 90
            angles.append(angle)

        # 取中位数角度
        skew_angle = np.median(angles)

        # 角度太小则不矫正
        if abs(skew_angle) < 1.0:
            return image, 0.0

        # 旋转矫正
        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
        rotated = cv2.warpAffine(image, rotation_matrix, (width, height),
                                  borderMode=cv2.BORDER_REPLICATE)

        return rotated, skew_angle

    @staticmethod
    def preprocess_for_ocr(image_path: str) -> np.ndarray:
        """OCR预处理流水线

        Args:
            image_path: 图片路径

        Returns:
            预处理后的图片
        """
        # 1. 加载图片
        image = ImageProcessor.load_image(image_path)

        # 2. 矫正倾斜
        image, _ = ImageProcessor.correct_skew(image)

        # 3. 去噪
        image = ImageProcessor.denoise_image(image)

        # 4. 增强对比度
        image = ImageProcessor.enhance_contrast(image)

        return image

    @staticmethod
    def validate_image(image_path: str) -> Tuple[bool, str]:
        """验证图片是否符合要求

        Args:
            image_path: 图片路径

        Returns:
            (是否有效, 错误信息)
        """
        try:
            image = ImageProcessor.load_image(image_path)

            height, width = image.shape[:2]

            # 检查最小尺寸
            if width < ocr_config.image_min_width:
                return False, f"图片宽度太小: {width} < {ocr_config.image_min_width}"

            if height < ocr_config.image_min_height:
                return False, f"图片高度太小: {height} < {ocr_config.image_min_height}"

            # 检查最大尺寸（分别检查宽度和高度）
            max_width = getattr(ocr_config, 'image_max_width', ocr_config.image_max_size)
            max_height = getattr(ocr_config, 'image_max_height', ocr_config.image_max_size)

            if width > max_width:
                return False, f"图片宽度超限: {width} > {max_width}"

            if height > max_height:
                return False, f"图片高度超限: {height} > {max_height}"

            return True, ""

        except Exception as e:
            return False, str(e)

    @staticmethod
    def validate_pdf(file_path: str) -> Tuple[bool, str]:
        """验证PDF文件是否符合要求

        Args:
            file_path: PDF文件路径

        Returns:
            (是否有效, 错误信息)
        """
        try:
            if not Path(file_path).exists():
                return False, f"文件不存在: {file_path}"

            # 检查文件大小（≤ 20MB）
            file_size = Path(file_path).stat().st_size
            max_pdf_size = 20 * 1024 * 1024  # 20MB
            if file_size > max_pdf_size:
                return False, f"PDF文件大小不能超过20MB"

            # 检查页数（≤ 20页）
            try:
                import pypdfium2 as pdfium
                doc = pdfium.PdfDocument(file_path)
                try:
                    page_count = len(doc)
                finally:
                    doc.close()
                if page_count > 20:
                    return False, f"PDF页数不能超过20页"
            except ImportError:
                logger.warning("pypdfium2 未安装，跳过PDF页数校验")
            except Exception as e:
                return False, f"PDF文件无法读取: {str(e)}"

            return True, "OK"

        except Exception as e:
            return False, str(e)


# 全局实例
image_processor = ImageProcessor()
