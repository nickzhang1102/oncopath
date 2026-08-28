"""oncopath ↔ AgentTeams 集成契约（v1）本地镜像。

两端共同维护的契约事实：端点路径、版本握手、限额、规范状态集、错误码与
载荷字段。远端（agentTeams）的 ``GET /api/integrations/v1/{client_key}/capabilities``
是运行时权威源；本模块提供默认常量、capabilities 探测与错误码分类，调用侧
按契约消费，而不是按猜测适配远端行为。

镜像关系：
- 常量 ↔ agentTeams ``services/agentteams_integration_launch.py``
- 错误码/限额 ↔ agentTeams 契约文档 ``docs/deployment/integration-clients.md``
"""

import json
import logging
import time
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

PROVIDER = "agentteams"
CLIENT_LOCALE = "zh-CN"
# 调用方声明支持的协议版本（随 capabilities 探测结果校验）。
PROTOCOL_VERSION = 1
MIN_PROTOCOL_VERSION = 1
INTEGRATION_API_VERSION = "v1"

CAPABILITIES_TIMEOUT_SECONDS = 5.0
CAPABILITIES_CACHE_TTL_SECONDS = 60

# 与 agentTeams INTEGRATION_LIMITS 保持一致的默认限额；
# 运行时以 capabilities 宣告为准，探测失败时使用这些值兜底。
DEFAULT_LIMITS = {
    "message_max_length": 100_000,
    "metadata_max_length": 20_000,
    "request_id_max_length": 100,
    "title_max_length": 500,
    "ref_max_length": 100,
    "min_message_length": 1,
}

# 规范状态集（launch/status 响应；not_found 仅出现在查询响应中）。
REMOTE_STATUSES = frozenset({"created", "running", "completed", "failed", "stopped", "not_found"})
TERMINAL_STATUSES = frozenset({"completed", "failed", "stopped"})

_capabilities_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def effective_client_key() -> str:
    """部署级集成客户端身份（agentTeams ``integration_clients.client_key``）。

    归一化逻辑只此一处：空值回落到 "agentteams"，供启动调用与能力探测共用。
    """
    return (settings.AGENTTEAMS_CLIENT_KEY or "agentteams").strip() or "agentteams"


def _capabilities_cache_key(base_url: str, client_key: str) -> str:
    return f"{base_url}|{client_key}"


def build_agentteams_api_base(base_url: str) -> str:
    """把配置里的 base_url 解析为可调用的 API 源（同站反代 / 本地 HTTP / HTTPS）。"""
    base = base_url.rstrip("/")
    if base.startswith("https://"):
        return base
    if base.startswith("http://"):
        if urlparse(base).hostname in {"localhost", "127.0.0.1", "::1"}:
            return base
        raise HTTPException(
            status_code=503,
            detail={"error": "agentteams_not_configured", "message": "AgentTeams 地址必须使用 HTTPS"},
        )
    if base.startswith("/"):
        origin = settings.AGENTTEAMS_INTERNAL_ORIGIN.rstrip("/")
        if origin:
            return f"{origin}{base}"
    raise HTTPException(
        status_code=503,
        detail={"error": "agentteams_not_configured", "message": "AgentTeams 地址配置无效"},
    )


def build_embed_url(base_url: str, embed_path: str) -> str:
    base = base_url.rstrip("/")
    path = embed_path if embed_path.startswith("/") else f"/{embed_path}"
    return f"{base}{path}"


def integration_launch_url(base_url: str, client_key: str) -> str:
    return f"{build_agentteams_api_base(base_url)}/api/integrations/{INTEGRATION_API_VERSION}/{client_key}/consultation-launches"


def integration_launch_status_url(base_url: str, client_key: str, request_id: str) -> str:
    return (
        f"{build_agentteams_api_base(base_url)}/api/integrations/{INTEGRATION_API_VERSION}/"
        f"{client_key}/consultation-launches/{request_id}"
    )


def integration_embed_reissue_url(base_url: str, client_key: str, request_id: str) -> str:
    """远端重签端点：为既有启动铸造一个新嵌入令牌（不创建/不重启工作流）。

    远端实现 ``agentTeams services/agentteams_integration_launch.py::reissue_agentteams_embed_token``，
    由 ``POST /api/integrations/v1/{client_key}/consultation-launches/{request_id}/embed-token`` 暴露。
    """
    return (
        f"{build_agentteams_api_base(base_url)}/api/integrations/{INTEGRATION_API_VERSION}/"
        f"{client_key}/consultation-launches/{request_id}/embed-token"
    )


def integration_capabilities_url(base_url: str, client_key: str) -> str:
    return (
        f"{build_agentteams_api_base(base_url)}/api/integrations/{INTEGRATION_API_VERSION}/"
        f"{client_key}/capabilities"
    )


def integration_headers(integration_secret: str, request_id: str | None = None) -> dict[str, str]:
    """契约请求头：鉴权 + 版本声明；启动时附加幂等 request-id。"""
    headers = {
        "X-Integration-Key": integration_secret,
        "X-Integration-Protocol-Version": str(PROTOCOL_VERSION),
    }
    if request_id is not None:
        headers["X-Request-Id"] = request_id
    return headers


def clear_capabilities_cache() -> None:
    """测试与配置变更后清空探测缓存。"""
    _capabilities_cache.clear()


async def fetch_agentteams_capabilities(
    base_url: str,
    integration_secret: str,
    client_key: str,
) -> dict[str, Any] | None:
    """探测远端能力宣告；任何失败返回 None，绝不向调用方抛错。

    结果按 base_url+client_key 缓存 CAPABILITIES_CACHE_TTL_SECONDS，
    避免每次启动/可用性查询都打一次远端。
    """
    key = _capabilities_cache_key(base_url, client_key)
    now = time.monotonic()
    cached = _capabilities_cache.get(key)
    if cached is not None and cached[0] + CAPABILITIES_CACHE_TTL_SECONDS > now:
        return cached[1]
    url = integration_capabilities_url(base_url, client_key)
    try:
        async with httpx.AsyncClient(timeout=CAPABILITIES_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers=integration_headers(integration_secret))
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        logger.warning("AgentTeams capabilities 探测失败: url=%s error=%s", url, exc)
        return None
    if response.status_code >= 400:
        logger.warning(
            "AgentTeams capabilities 探测被拒绝: status=%s body=%s",
            response.status_code,
            response.text[:200],
        )
        return None
    try:
        payload = response.json()
    except ValueError:
        logger.warning("AgentTeams capabilities 返回非 JSON: url=%s", url)
        return None
    if not isinstance(payload, dict):
        return None
    _capabilities_cache[key] = (now, payload)
    return payload


def effective_limits(capabilities: dict[str, Any] | None) -> dict[str, Any]:
    """远端宣告限额优先，缺失字段回退到默认值。"""
    remote = capabilities.get("limits") if capabilities else None
    if isinstance(remote, dict) and remote:
        return {**DEFAULT_LIMITS, **remote}
    return dict(DEFAULT_LIMITS)


async def validate_launch_payload(
    base_url: str,
    integration_secret: str,
    client_key: str,
    payload: dict[str, Any],
    request_id: str | None,
) -> None:
    """发送前按远端宣告限额预校验，返回时 payload 可直接发送。

    超限返回 422 业务错误，不把超限请求送到远端换一个 400。
    """
    capabilities = await fetch_agentteams_capabilities(base_url, integration_secret, client_key)
    limits = effective_limits(capabilities)

    message = str(payload.get("message") or "")
    message_max = int(limits.get("message_max_length") or DEFAULT_LIMITS["message_max_length"])
    if len(message) > message_max:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "agentteams_payload_too_large",
                "message": f"会诊材料超过 {message_max} 字符上限，请精简后重试",
            },
        )

    metadata = payload.get("metadata")
    if metadata is not None:
        try:
            metadata_size = len(json.dumps(metadata, ensure_ascii=False))
        except (TypeError, ValueError):
            metadata_size = 0
        metadata_max = int(limits.get("metadata_max_length") or DEFAULT_LIMITS["metadata_max_length"])
        if metadata_size > metadata_max:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "agentteams_payload_too_large",
                    "message": f"辅助元数据超过 {metadata_max} 字符上限，请精简后重试",
                },
            )

    if request_id is not None:
        request_id_max = int(limits.get("request_id_max_length") or DEFAULT_LIMITS["request_id_max_length"])
        if len(str(request_id)) > request_id_max:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "agentteams_payload_too_large",
                    "message": f"启动标识超过 {request_id_max} 字符上限",
                },
            )

    title = payload.get("title")
    if title is not None:
        title_max = int(limits.get("title_max_length") or DEFAULT_LIMITS["title_max_length"])
        if len(str(title)) > title_max:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "agentteams_payload_too_large",
                    "message": f"会诊标题超过 {title_max} 字符上限",
                },
            )

    ref_max = int(limits.get("ref_max_length") or DEFAULT_LIMITS["ref_max_length"])
    for field in ("user_ref", "subject_ref", "conversation_ref"):
        value = payload.get(field)
        if value is not None and len(str(value)) > ref_max:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "agentteams_payload_too_large",
                    "message": f"引用字段 {field} 超过 {ref_max} 字符上限",
                },
            )


def map_remote_error(status_code: int, error_code: str, message: str) -> tuple[int, str, str]:
    """把远端 ``detail{error, message}`` 归一为产品化业务错误。

    契约以远端错误码为准；未知码不再静默折叠成"不可用"，而是记录原始码
    并按 HTTP 语义分类，保证排障可追溯。
    """
    table = {
        "invalid_integration_key": (
            502, "agentteams_invalid_integration_key", "AgentTeams 集成密钥无效",
        ),
        "service_account_not_configured": (
            403, "agentteams_service_account_not_configured", "AgentTeams 服务账户未配置",
        ),
        "integration_disabled": (
            403, "agentteams_integration_disabled", "AgentTeams 集成未启用",
        ),
        "integration_capability_disabled": (
            403, "agentteams_integration_disabled", "AgentTeams 集成能力未启用",
        ),
        "unsupported_version": (
            426, "agentteams_unsupported_version", "AgentTeams 版本不兼容",
        ),
        "idempotency_conflict": (
            409, "agentteams_idempotency_conflict", "该启动标识已用于其他会诊，请重新发起",
        ),
        "invalid_payload": (
            400, "agentteams_payload_rejected", "AgentTeams 拒绝了本次请求载荷",
        ),
        "invalid_client": (
            503, "agentteams_invalid_client_key", "AgentTeams 部署未注册该集成客户端",
        ),
        "integration_client_not_found": (
            503, "agentteams_invalid_client_key", "AgentTeams 部署未注册该集成客户端",
        ),
        "integration_adapter_unavailable": (
            502, "agentteams_unavailable", "AgentTeams 服务暂时不可用",
        ),
        "agentteams_launch_not_found": (
            404, "agentteams_launch_not_found", "该会诊在 AgentTeams 侧无启动记录，请从会诊历史重新发起或联系管理员",
        ),
        "agentteams_launch_failed": (
            409, "agentteams_launch_failed", "该会诊已在 AgentTeams 侧执行失败，无法打开",
        ),
        "agentteams_launch_stopped": (
            409, "agentteams_launch_stopped", "该会诊已在 AgentTeams 侧停止运行，无法打开",
        ),
    }
    if error_code in table:
        return table[error_code]
    logger.warning(
        "AgentTeams 返回未登记错误码: status=%s code=%s message=%s",
        status_code,
        error_code,
        message,
    )
    # 未知码不回显远端 message（避免内部细节外泄），按 HTTP 语义选择兜底展示。
    if 400 <= status_code < 500:
        return (400, "agentteams_payload_rejected", "AgentTeams 拒绝了本次请求")
    return (502, "agentteams_unavailable", "AgentTeams 服务暂时不可用")


def first_present(result: dict[str, Any], *names: str) -> Any:
    """按优先级读取响应字段（中立字段优先，遗留字段回退）。"""
    for name in names:
        value = result.get(name)
        if value is not None:
            return value
    return None