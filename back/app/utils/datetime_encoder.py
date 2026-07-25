"""自定义 JSON 编码器

为整个 FastAPI 应用统一处理 datetime 字段的序列化：
- naive datetime（数据库中存的 UTC） → 显式带 Z 后缀
- aware datetime → 标准化为 UTC + Z 后缀

解决问题：原 FastAPI 默认 jsonable_encoder 对 naive datetime 输出
"2026-06-03T12:43:00"（无时区标识），前端 dayjs / new Date() 会
将其按本地时区（UTC+8）解析，导致显示时间与实际相差 8 小时。

设计思路：
- 继承 fastapi.encoders.jsonable_encoder，注册自定义 datetime encoder
- 提供 UTCJSONResponse，作为 FastAPI 的 default_response_class
- 这样所有路由返回的 dict / Pydantic Model 都会经过该编码器
"""

from datetime import datetime
from typing import Any

from fastapi.encoders import jsonable_encoder as _fastapi_jsonable_encoder
from fastapi.responses import JSONResponse

from app.utils.time_utils import utc_isoformat


def _encode_datetime(obj: datetime) -> str:
    """datetime 对象的自定义编码器：统一使用 Z 后缀的 UTC ISO 8601 格式"""
    return utc_isoformat(obj)


def utc_jsonable_encoder(obj: Any, **kwargs: Any) -> Any:
    """包装 FastAPI 的 jsonable_encoder，注入 datetime 自定义编码器

    通过 `custom_encoder` 参数覆盖默认的 datetime 编码器（默认输出无时区字符串），
    使其统一输出带 Z 后缀的 UTC ISO 8601 字符串。
    """
    custom = kwargs.pop("custom_encoder", {}) or {}
    custom[datetime] = _encode_datetime
    return _fastapi_jsonable_encoder(obj, custom_encoder=custom, **kwargs)


class UTCJSONResponse(JSONResponse):
    """统一使用 utc_jsonable_encoder 的 JSON 响应

    通过 `default_response_class=UTCJSONResponse` 全局应用，
    所有未显式指定 response_class 的路由都会继承此行为。
    """

    def render(self, content: Any) -> bytes:
        return super().render(utc_jsonable_encoder(content))
