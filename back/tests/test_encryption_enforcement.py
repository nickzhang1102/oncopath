"""加密服务强制校验测试 — ENCRYPTION_KEY 未配置时拒绝启动"""
import sys
import os
import types
import pytest
from unittest.mock import patch
from pydantic import ValidationError

# 直接导入 config 模块，绕过 app/__init__.py 的 PaddleOCR 依赖
_back_dir = os.path.join(os.path.dirname(__file__), "..")
_back_dir = os.path.abspath(_back_dir)
_app_dir = os.path.join(_back_dir, "app")
_core_dir = os.path.join(_app_dir, "core")

if _back_dir not in sys.path:
    sys.path.insert(0, _back_dir)

if "app" not in sys.modules:
    app_mod = types.ModuleType("app")
    app_mod.__path__ = [_app_dir]
    app_mod.__package__ = "app"
    sys.modules["app"] = app_mod

if "app.core" not in sys.modules:
    core_mod = types.ModuleType("app.core")
    core_mod.__path__ = [_core_dir]
    core_mod.__package__ = "app.core"
    sys.modules["app.core"] = core_mod

from app.core.config import Settings  # noqa: E402


def test_encryption_key_required_by_default():
    """ENCRYPTION_KEY 为空且未显式允许时应拒绝启动"""
    with pytest.raises(ValidationError, match="ENCRYPTION_KEY"):
        Settings(ENCRYPTION_KEY="", SECRET_KEY="a" * 32, ALLOW_UNENCRYPTED_PHI=False)


def test_encryption_key_allows_dev_override():
    """ALLOW_UNENCRYPTED_PHI=true 时允许空 ENCRYPTION_KEY"""
    settings = Settings(
        ENCRYPTION_KEY="", SECRET_KEY="a" * 32, ALLOW_UNENCRYPTED_PHI=True
    )
    assert settings.ENCRYPTION_KEY == ""
    assert settings.ALLOW_UNENCRYPTED_PHI is True


def test_encryption_key_valid_accepted():
    """有效的 Fernet 密钥应被正常接受"""
    from cryptography.fernet import Fernet

    valid_key = Fernet.generate_key().decode()
    settings = Settings(
        ENCRYPTION_KEY=valid_key, SECRET_KEY="a" * 32
    )
    assert settings.ENCRYPTION_KEY == valid_key


def test_encryption_key_invalid_format_rejected():
    """无效格式的 ENCRYPTION_KEY 应被拒绝"""
    with pytest.raises(ValidationError, match="ENCRYPTION_KEY"):
        Settings(ENCRYPTION_KEY="not-a-valid-key", SECRET_KEY="a" * 32)


def test_encryption_service_raises_without_key():
    """EncryptionService 在无密钥且未允许明文时应抛出 RuntimeError"""
    from app.services.encryption_service import EncryptionService

    with patch("app.services.encryption_service.settings") as mock_settings:
        mock_settings.ENCRYPTION_KEY = ""
        mock_settings.ALLOW_UNENCRYPTED_PHI = False
        with pytest.raises(RuntimeError, match="ENCRYPTION_KEY"):
            EncryptionService().encrypt("test")


def test_encryption_service_warns_with_dev_override():
    """EncryptionService 在开发模式下应打印警告而非抛异常"""
    from app.services.encryption_service import EncryptionService

    with patch("app.services.encryption_service.settings") as mock_settings:
        mock_settings.ENCRYPTION_KEY = ""
        mock_settings.ALLOW_UNENCRYPTED_PHI = True
        service = EncryptionService()
        assert service.encrypt("test") == "test"
        assert service._fernet is None
        assert service.decrypt("test") == "test"


def test_encryption_service_works_with_valid_key():
    """EncryptionService 在有效密钥时应正常加密解密"""
    from app.services.encryption_service import EncryptionService

    with patch("app.services.encryption_service.settings") as mock_settings:
        from cryptography.fernet import Fernet

        valid_key = Fernet.generate_key().decode()
        mock_settings.ENCRYPTION_KEY = valid_key
        mock_settings.ALLOW_UNENCRYPTED_PHI = False
        service = EncryptionService()
        encrypted = service.encrypt("hello")
        assert service._fernet is not None
        assert encrypted != "hello"
        assert service.decrypt(encrypted) == "hello"
