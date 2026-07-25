"""API速率限制配置

统一管理 SlowAPI Limiter 实例，避免循环导入。
所有路由文件从此模块导入 limiter。

开发/测试环境自动禁用限流，生产环境启用。
可通过 RATE_LIMIT_ENABLED 环境变量覆盖。
"""
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

# 环境变量优先，未设置时根据 DEBUG 判断
_env_val = os.getenv("RATE_LIMIT_ENABLED")
if _env_val is not None:
    _rate_limit_enabled = _env_val.lower() in ("true", "1", "yes")
else:
    # DEBUG=true 时禁用限流（开发/测试环境）
    _rate_limit_enabled = not os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

# 全局限流器实例（默认100/分钟）
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    enabled=_rate_limit_enabled
)