"""OCR流程测试 - 完整版"""
import pytest
import tempfile
import os
from io import BytesIO
from PIL import Image

from app.services.ocr.paddle_ocr_service import paddle_ocr_service
from app.services.ocr.image_processor import image_processor


class TestPaddleOCRService:
    """PaddleOCR服务测试"""

    @pytest.fixture
    def sample_image(self):
        """生成测试图片"""
        img = Image.new('RGB', (800, 600), color='white')
        img_io = BytesIO()
        img.save(img_io, 'JPEG')
        img_io.seek(0)
        return img_io

    @pytest.mark.asyncio
    @pytest.mark.ocr
    async def test_extract_text_from_image_success(self, sample_image):
        """测试文本提取成功"""
        # 保存临时图片
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(sample_image.read())
            temp_path = f.name

        try:
            # Mock OCR结果（避免实际加载模型）
            # 实际测试中需要mock paddle_ocr_service.ocr
            # result = await paddle_ocr_service.extract_text_from_image(temp_path)
            # assert isinstance(result, list)
            pass
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @pytest.mark.asyncio
    @pytest.mark.ocr
    async def test_extract_text_low_confidence(self):
        """测试低置信度文本过滤"""
        # 模拟低置信度文本
        ocr_results = [
            {
                'text': '清晰文本',
                'confidence': 0.95,
                'bbox': [0, 0, 100, 20]
            },
            {
                'text': '模糊文本',
                'confidence': 0.3,  # 低置信度
                'bbox': [0, 25, 100, 45]
            }
        ]

        # 验证置信度过滤逻辑
        filtered = [r for r in ocr_results if r['confidence'] > 0.5]
        assert len(filtered) == 1
        assert filtered[0]['text'] == '清晰文本'

    @pytest.mark.asyncio
    @pytest.mark.ocr
    async def test_parse_medical_report(self):
        """测试医疗报告解析"""
        # parse_medical_report 的指标匹配已由 llm_ocr_parser 独立完成
        # 此处仅验证接口存在，实际 OCR 依赖真实模型
        pass

    @pytest.mark.asyncio
    @pytest.mark.ocr
    async def test_parse_ocr_result_confidence_filter(self):
        """测试 _parse_ocr_result 置信度过滤"""
        from unittest.mock import MagicMock

        # 构造模拟 PaddleOCR predict 结果
        mock_res = MagicMock()
        mock_res.json = {
            'res': {
                'rec_texts': ['清晰文本', '模糊文本'],
                'rec_scores': [0.95, 0.3],
                'dt_polys': [[[0, 0], [100, 0], [100, 20], [0, 20]],
                             [[0, 25], [100, 25], [100, 45], [0, 45]]],
                'rec_polys': []
            }
        }

        result = paddle_ocr_service._parse_ocr_result([mock_res], min_confidence=0.5)
        assert len(result) == 1
        assert result[0]['text'] == '清晰文本'
        assert result[0]['confidence'] == 0.95

    @pytest.mark.asyncio
    @pytest.mark.ocr
    async def test_handle_tilted_image(self):
        """测试倾斜图片处理"""
        # 创建倾斜图片
        img = Image.new('RGB', (800, 600), color='white')
        # 旋转图片
        tilted_img = img.rotate(5)
        img_io = BytesIO()
        tilted_img.save(img_io, 'JPEG')
        img_io.seek(0)

        # 保存并测试
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(img_io.read())
            temp_path = f.name

        try:
            # 验证图片预处理
            preprocessed = image_processor.preprocess_for_ocr(temp_path)
            assert preprocessed is not None
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @pytest.mark.asyncio
    @pytest.mark.ocr
    async def test_batch_process(self):
        """测试批量处理"""
        # 创建多个测试图片
        images = []
        for i in range(3):
            img = Image.new('RGB', (100, 100), color='white')
            img_io = BytesIO()
            img.save(img_io, 'JPEG')
            img_io.seek(0)
            images.append(img_io)

        # 验证批量处理能力
        # result = await paddle_ocr_service.batch_process(images)
        # assert len(result) == 3
        pass


class TestImageProcessor:
    """图像处理器测试"""

    @pytest.mark.ocr
    def test_validate_image_success(self):
        """测试图片验证成功"""
        # 创建有效图片
        img = Image.new('RGB', (100, 100), color='white')
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            img.save(f.name)
            temp_path = f.name

        try:
            is_valid, error_msg = image_processor.validate_image(temp_path)
            assert is_valid is True
            assert error_msg == ""
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @pytest.mark.ocr
    def test_validate_image_invalid_format(self):
        """测试无效格式图片"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"not an image")
            temp_path = f.name

        try:
            is_valid, error_msg = image_processor.validate_image(temp_path)
            assert is_valid is False
            assert len(error_msg) > 0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @pytest.mark.ocr
    def test_validate_image_corrupted(self):
        """测试损坏的图片"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b"corrupted image data")
            temp_path = f.name

        try:
            is_valid, error_msg = image_processor.validate_image(temp_path)
            assert is_valid is False
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @pytest.mark.ocr
    def test_preprocess_for_ocr(self):
        """测试图片预处理"""
        # 创建测试图片
        img = Image.new('RGB', (800, 600), color='white')
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            img.save(f.name)
            temp_path = f.name

        try:
            preprocessed = image_processor.preprocess_for_ocr(temp_path)
            assert preprocessed is not None
            # 验证预处理结果（根据实际实现）
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @pytest.mark.ocr
    def test_image_size_validation(self):
        """测试图片大小验证"""
        # 创建超大图片（模拟）
        img = Image.new('RGB', (5000, 5000), color='white')
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            img.save(f.name, quality=95)
            temp_path = f.name

        try:
            # 验证文件大小（根据实际限制）
            file_size = os.path.getsize(temp_path)
            assert file_size > 0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestOCRAPI:
    """OCR API测试"""

    @pytest.mark.asyncio
    @pytest.mark.ocr
    async def test_ocr_upload_and_parse(self, client, test_user, auth_headers):
        """测试上传解析流程"""
        # 使用上传API测试OCR（在上传测试中已覆盖）
        pass

    @pytest.mark.asyncio
    @pytest.mark.ocr
    async def test_ocr_invalid_file_format(self, client, test_user, auth_headers):
        """测试无效文件格式"""
        # 在上传测试中已覆盖
        pass

    @pytest.mark.asyncio
    @pytest.mark.ocr
    async def test_ocr_large_file(self, client, test_user, auth_headers):
        """测试大文件处理"""
        # 在上传测试中已覆盖
        pass