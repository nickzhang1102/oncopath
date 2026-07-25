"""OCR服务模块。

OCR 依赖 PaddleOCR/OpenCV 等较重的可选包。包初始化保持轻量，避免普通
API 启动或非 OCR 测试在 import `app.services.ocr.*` 时被这些依赖阻断。
"""

__all__ = [
    'PaddleOCRService',
    'paddle_ocr_service',
    'ImageProcessor',
    'image_processor',
    'LLMOCRParser',
    'llm_ocr_parser',
    'OCRIntegrationService',
    'ocr_integration_service',
    'OCRConfig',
    'ocr_config',
]


def __getattr__(name):
    if name in {'PaddleOCRService', 'paddle_ocr_service'}:
        from .paddle_ocr_service import PaddleOCRService, paddle_ocr_service
        return {'PaddleOCRService': PaddleOCRService, 'paddle_ocr_service': paddle_ocr_service}[name]
    if name in {'ImageProcessor', 'image_processor'}:
        from .image_processor import ImageProcessor, image_processor
        return {'ImageProcessor': ImageProcessor, 'image_processor': image_processor}[name]
    if name in {'LLMOCRParser', 'llm_ocr_parser'}:
        from .llm_ocr_parser import LLMOCRParser, llm_ocr_parser
        return {'LLMOCRParser': LLMOCRParser, 'llm_ocr_parser': llm_ocr_parser}[name]
    if name in {'OCRIntegrationService', 'ocr_integration_service'}:
        from .ocr_integration_service import OCRIntegrationService, ocr_integration_service
        return {
            'OCRIntegrationService': OCRIntegrationService,
            'ocr_integration_service': ocr_integration_service,
        }[name]
    if name in {'OCRConfig', 'ocr_config'}:
        from .ocr_config import OCRConfig, ocr_config
        return {'OCRConfig': OCRConfig, 'ocr_config': ocr_config}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
