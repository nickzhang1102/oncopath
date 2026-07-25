import sys
import os
import importlib
import pytest
from pydantic import ValidationError

# 直接导入 config 模块，绕过 app/__init__.py 的 PaddleOCR 依赖
# 将 app/core 的父目录加入 sys.path，然后直接 import config
_back_dir = os.path.join(os.path.dirname(__file__), "..")
_back_dir = os.path.abspath(_back_dir)
_app_dir = os.path.join(_back_dir, "app")
_core_dir = os.path.join(_app_dir, "core")

# 确保 app.core.config 可被直接加载而不触发 app/__init__.py
if _back_dir not in sys.path:
    sys.path.insert(0, _back_dir)

# 临时阻止 app/__init__.py 的自动加载
# 通过先注册一个空的 app 模块
if "app" not in sys.modules:
    import types
    app_mod = types.ModuleType("app")
    app_mod.__path__ = [_app_dir]
    app_mod.__package__ = "app"
    sys.modules["app"] = app_mod

if "app.core" not in sys.modules:
    import types
    core_mod = types.ModuleType("app.core")
    core_mod.__path__ = [_core_dir]
    core_mod.__package__ = "app.core"
    sys.modules["app.core"] = core_mod

# 现在可以安全导入 Settings
from app.core.config import Settings  # noqa: E402


def test_secret_key_default_rejected():
    """默认 SECRET_KEY 必须在启动时被拒绝"""
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(SECRET_KEY="your-secret-key-change-in-production")


def test_secret_key_empty_rejected():
    """空 SECRET_KEY 必须被拒绝"""
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(SECRET_KEY="")


def test_secret_key_valid_accepted():
    """合法 SECRET_KEY 应被接受"""
    s = Settings(SECRET_KEY="a" * 32, DB_PASSWORD="test")
    assert len(s.SECRET_KEY) >= 32
