"""LLM 配置运行时重载服务

从数据库读取 is_active=True 的配置，覆盖 Settings 属性，销毁旧 LLM 单例触发延迟重建。
"""
import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.admin import LLMConfig
from app.services.encryption_service import encryption_service

logger = logging.getLogger(__name__)

# config_key → Settings 属性名映射
_CONFIG_KEY_TO_ATTR: dict[str, str] = {
    # 会诊组
    "consultation_api_key": "LLM_API_KEY",
    "consultation_api_base": "LLM_API_BASE",
    "consultation_model_name": "LLM_MODEL_NAME",
    "consultation_timeout": "LLM_TIMEOUT",
    # 解读组
    "interpretation_api_key": "INTERPRETATION_LLM_API_KEY",
    "interpretation_api_base": "INTERPRETATION_LLM_API_BASE",
    "interpretation_model_name": "INTERPRETATION_LLM_MODEL_NAME",
    "interpretation_timeout": "INTERPRETATION_LLM_TIMEOUT",
    # OCR 组
    "ocr_api_key": "OCR_LLM_API_KEY",
    "ocr_api_base": "OCR_LLM_API_BASE",
    "ocr_model_name": "OCR_LLM_MODEL_NAME",
    "ocr_timeout": "OCR_LLM_TIMEOUT",
    "ocr_max_tokens": "OCR_LLM_MAX_TOKENS",
}

# 配置项元数据定义（表为空时用于构造展示列表）
LLM_CONFIG_DEFINITIONS = [
    # (config_key, config_group, display_name, description, is_secret)
    ("consultation_api_key", "consultation", "API Key", "会诊用 LLM API Key", True),
    ("consultation_api_base", "consultation", "API 地址", "会诊用 LLM API 地址", False),
    ("consultation_model_name", "consultation", "模型名称", "会诊用 LLM 模型名称", False),
    ("consultation_timeout", "consultation", "超时时间(秒)", "会诊用 LLM 请求超时", False),
    ("interpretation_api_key", "interpretation", "API Key", "解读用 LLM API Key", True),
    ("interpretation_api_base", "interpretation", "API 地址", "解读用 LLM API 地址", False),
    ("interpretation_model_name", "interpretation", "模型名称", "解读用 LLM 模型名称", False),
    ("interpretation_timeout", "interpretation", "超时时间(秒)", "解读用 LLM 请求超时", False),
    ("ocr_api_key", "ocr", "API Key", "OCR 用 LLM API Key", True),
    ("ocr_api_base", "ocr", "API 地址", "OCR 用 LLM API 地址", False),
    ("ocr_model_name", "ocr", "模型名称", "OCR 用 LLM 模型名称", False),
    ("ocr_timeout", "ocr", "超时时间(秒)", "OCR 用 LLM 请求超时", False),
    ("ocr_max_tokens", "ocr", "最大 Token 数", "OCR 用 LLM 最大输出 Token", False),
]

# interpretation 组的 property 映射（回退到 LLM_*）
_INTERPRETATION_PROPERTY = {
    "interpretation_api_key": "interpretation_api_key",
    "interpretation_api_base": "interpretation_api_base",
    "interpretation_model_name": "interpretation_model_name",
    "interpretation_timeout": "interpretation_timeout",
}

# config_group → 需要销毁的单例模块
_GROUP_SINGLETONS: dict[str, list[str]] = {
    "consultation": ["app.services.llm_service"],
    "interpretation": [],  # InterpretationService 非单例，每次 new 时从 settings 读
    "ocr": ["app.services.ocr.openai_llm_service"],
}


class LLMConfigService:
    """LLM 配置运行时重载"""

    @staticmethod
    def get_effective_value(config_key: str) -> str:
        """获取 config_key 对应的当前生效值（从 Settings 读取，含 interpretation 回退）"""
        if config_key in _INTERPRETATION_PROPERTY:
            return str(getattr(settings, _INTERPRETATION_PROPERTY[config_key], ""))
        attr_name = _CONFIG_KEY_TO_ATTR.get(config_key)
        if not attr_name:
            return ""
        return str(getattr(settings, attr_name, ""))

    def apply_configs(self, active_configs: List[LLMConfig]) -> None:
        """将活跃配置写入 Settings 并销毁相关单例

        注意：本方法为同步调用，在 async 单进程中不会被协程中断，
        因此不存在竞态窗口。多 worker 进程间配置不一致需通过
        共享存储（如 Redis pub/sub）解决，当前未实现。
        """
        # 1. 先销毁受影响组的 LLM 单例（旧实例不再接收新请求）
        affected_groups = set(cfg.config_group for cfg in active_configs)
        for group in affected_groups:
            self._destroy_singletons(group)

        # 2. 覆盖 Settings 属性（新实例创建时读取新值）
        for cfg in active_configs:
            attr_name = _CONFIG_KEY_TO_ATTR.get(cfg.config_key)
            if not attr_name:
                logger.warning(f"未知 config_key: {cfg.config_key}，跳过")
                continue

            old_value = getattr(settings, attr_name, None)
            # 解密 is_secret 的配置值，兼容明文旧数据
            if cfg.is_secret:
                try:
                    raw_value = encryption_service.decrypt(cfg.config_value)
                except (ValueError, Exception):
                    logger.info(f"{cfg.config_key} 解密失败，视为明文（首次加密迁移）")
                    raw_value = cfg.config_value
            else:
                raw_value = cfg.config_value
            # 类型转换：timeout/max_tokens 需要整数
            if attr_name.endswith(("TIMEOUT", "MAX_TOKENS")):
                try:
                    new_value = int(raw_value)
                except (ValueError, TypeError):
                    logger.warning(f"{cfg.config_key} 值 '{raw_value}' 无法转为整数，跳过")
                    continue
            else:
                new_value = raw_value

            # API Key 不允许设为空字符串
            if attr_name.endswith("_API_KEY") and not new_value:
                logger.warning(f"{cfg.config_key} 值为空，跳过（避免服务不可用）")
                continue

            setattr(settings, attr_name, new_value)
            is_secret = cfg.is_secret
            log_new = "****" if is_secret else new_value
            log_old = "****" if is_secret else old_value
            logger.info(f"Settings.{attr_name}: {log_old} → {log_new}")

    def _destroy_singletons(self, group: str) -> None:
        """销毁指定配置组的 LLM 服务单例"""
        modules = _GROUP_SINGLETONS.get(group, [])
        for module_path in modules:
            try:
                import importlib
                mod = importlib.import_module(module_path)

                if module_path == "app.services.llm_service":
                    mod._llm_service_instance = None
                    logger.info("已销毁 LLMService 单例")
                elif module_path == "app.services.ocr.openai_llm_service":
                    mod._openai_llm_service_instance = None
                    logger.info("已销毁 OpenAILLMService 单例")
            except Exception as e:
                logger.error(f"销毁 {module_path} 单例失败: {e}")

    @staticmethod
    async def load_and_apply(db: AsyncSession) -> int:
        """启动时从数据库加载活跃配置并应用到运行时

        返回应用的配置组数量；查询失败由调用方捕获处理。
        """
        result = await db.execute(
            select(LLMConfig).where(LLMConfig.is_active == True)  # noqa: E712
        )
        active_configs = result.scalars().all()
        if not active_configs:
            return 0
        LLMConfigService().apply_configs(active_configs)
        return len(set(c.config_group for c in active_configs))

    @staticmethod
    def is_configured() -> bool:
        """会诊组 LLM 是否已配置（API Key 非空），供首启弹窗判定"""
        return bool(settings.LLM_API_KEY)

    @staticmethod
    async def test_group(group: str) -> dict:
        """测试指定配置组的 LLM 连通性

        临时构造客户端发一条极短请求，验证 api_key/api_base/model 可用。
        返回 {"success": bool, "message": str, "latency_ms": int | None}
        """
        import time
        import httpx

        # 从 Settings 读取该组当前生效的配置
        group_attrs = {
            "consultation": ("LLM_API_KEY", "LLM_API_BASE", "LLM_MODEL_NAME"),
            "interpretation": ("INTERPRETATION_LLM_API_KEY", "INTERPRETATION_LLM_API_BASE", "INTERPRETATION_LLM_MODEL_NAME"),
            "ocr": ("OCR_LLM_API_KEY", "OCR_LLM_API_BASE", "OCR_LLM_MODEL_NAME"),
        }
        if group not in group_attrs:
            return {"success": False, "message": f"未知配置组: {group}", "latency_ms": None}

        key_attr, base_attr, model_attr = group_attrs[group]

        # interpretation 组有 property 回退
        if group == "interpretation":
            api_key = settings.interpretation_api_key
            api_base = settings.interpretation_api_base
            model = settings.interpretation_model_name
        else:
            api_key = getattr(settings, key_attr, "")
            api_base = getattr(settings, base_attr, "")
            model = getattr(settings, model_attr, "")

        if not api_key:
            return {"success": False, "message": "API Key 未配置", "latency_ms": None}
        if not api_base:
            return {"success": False, "message": "API 地址未配置", "latency_ms": None}
        if not model:
            return {"success": False, "message": "模型名称未配置", "latency_ms": None}

        base = api_base.rstrip('/')
        if base.endswith("/chat/completions"):
            url = base
        else:
            url = f"{base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
        }

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
            latency = int((time.monotonic() - start) * 1000)

            if resp.status_code == 200:
                return {"success": True, "message": f"连接成功 ({latency}ms)", "latency_ms": latency}
            else:
                detail = ""
                try:
                    body = resp.json()
                    detail = body.get("error", {}).get("message", resp.text[:200])
                except Exception:
                    detail = resp.text[:200]
                return {
                    "success": False,
                    "message": f"HTTP {resp.status_code}: {detail}",
                    "latency_ms": latency,
                }
        except httpx.TimeoutException:
            latency = int((time.monotonic() - start) * 1000)
            return {"success": False, "message": f"请求超时 ({latency}ms)", "latency_ms": latency}
        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            return {"success": False, "message": f"连接失败: {str(e)[:200]}", "latency_ms": latency}
