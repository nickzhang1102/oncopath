"""PaddleOCR CPU/GPU 设备选择的无硬件单元测试。"""
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.ocr.ocr_config import OCRConfig, ocr_config
from app.services.ocr.paddle_ocr_service import (
    PaddleOCRService,
    _configure_paddle_device,
)


class FakePaddle:
    def __init__(self, *, cuda_supported: bool = False, set_device_error=None):
        self.device = SimpleNamespace(is_compiled_with_cuda=lambda: cuda_supported)
        self.set_device_error = set_device_error
        self.selected_device = None
        self.flags = []

    def set_device(self, device):
        if self.set_device_error:
            raise self.set_device_error
        self.selected_device = device

    def set_flags(self, flags):
        self.flags.append(flags)


@pytest.mark.parametrize("device", ["cpu", "gpu", "gpu:0", "gpu:12"])
def test_ocr_config_accepts_supported_devices(device):
    assert OCRConfig(paddle_device=device).paddle_device == device


@pytest.mark.parametrize("device", ["cuda", "gpu:-1", "gpu:abc", "remote"])
def test_ocr_config_rejects_unsupported_devices(device):
    with pytest.raises(ValueError, match="OCR_PADDLE_DEVICE"):
        OCRConfig(paddle_device=device)


def test_configure_cpu_selects_cpu_and_disables_onednn():
    paddle = FakePaddle()

    _configure_paddle_device(paddle, "cpu")

    assert paddle.selected_device == "cpu"
    assert paddle.flags == [{"FLAGS_use_onednn": False}]


def test_configure_gpu_requires_cuda_wheel():
    paddle = FakePaddle(cuda_supported=False)

    with pytest.raises(RuntimeError, match="docker-compose.gpu.yml"):
        _configure_paddle_device(paddle, "gpu:0")

    assert paddle.selected_device is None


def test_configure_gpu_selects_requested_device_without_cpu_flags():
    paddle = FakePaddle(cuda_supported=True)

    _configure_paddle_device(paddle, "gpu:0")

    assert paddle.selected_device == "gpu:0"
    assert paddle.flags == []


def test_configure_gpu_reports_runtime_setup_failure():
    paddle = FakePaddle(cuda_supported=True, set_device_error=RuntimeError("driver missing"))

    with pytest.raises(RuntimeError, match="NVIDIA Container Toolkit"):
        _configure_paddle_device(paddle, "gpu:0")


def test_base_and_table_pipelines_use_same_configured_gpu(monkeypatch):
    fake_paddle = FakePaddle(cuda_supported=True)
    paddle_ocr_factory = MagicMock()
    table_factory = MagicMock()
    fake_paddleocr = SimpleNamespace(
        PaddleOCR=paddle_ocr_factory,
        TableRecognitionPipelineV2=table_factory,
    )
    service = PaddleOCRService()

    monkeypatch.setattr(ocr_config, "paddle_device", "gpu:0")
    with patch.dict(sys.modules, {"paddle": fake_paddle, "paddleocr": fake_paddleocr}):
        service._lazy_init()
        service._try_init_table()

    assert fake_paddle.selected_device == "gpu:0"
    paddle_ocr_factory.assert_called_once_with(
        lang=ocr_config.paddle_lang,
        device="gpu:0",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=ocr_config.paddle_use_angle_cls,
    )
    table_factory.assert_called_once_with(device="gpu:0")
