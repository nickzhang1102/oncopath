"""LLM 服务模块

使用 OpenAI 兼容 API 的异步服务模块，支持流式输出。
参照 claudechat 项目的 llm_service.py，适配 FastAPI 异步架构。
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Awaitable, Callable, Dict, List, Optional

import httpx
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

# 重试配置
RETRY_MAX_ATTEMPTS = 3
RETRY_BASE_INTERVAL = 5  # 基础重试间隔（秒），指数退避


def _is_timeout_error(error: Exception) -> bool:
    """判断是否为超时类错误"""
    if isinstance(error, (asyncio.TimeoutError, TimeoutError)):
        return True
    error_msg = str(error).lower()
    return 'timed out' in error_msg or 'timeout' in error_msg


def _calculate_retry_delay(attempt: int, is_timeout: bool) -> float:
    """计算重试延迟（指数退避）"""
    base = 15 if is_timeout else RETRY_BASE_INTERVAL
    delay = base * (2 ** (attempt - 1))
    return min(delay, 60)


class LLMService:
    """LLM API 集成服务（OpenAI 兼容，异步）"""

    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.model = settings.LLM_MODEL_NAME
        self.timeout = settings.LLM_TIMEOUT
        self._initialized = False

    def _initialize(self):
        """延迟初始化客户端"""
        if self._initialized:
            return

        try:
            if settings.LLM_API_KEY:
                timeout_config = httpx.Timeout(
                    connect=10.0,
                    read=float(self.timeout),
                    write=30.0,
                    pool=10.0,
                )

                client_kwargs: Dict = {
                    "api_key": settings.LLM_API_KEY,
                    "timeout": timeout_config,
                }
                if settings.LLM_API_BASE:
                    client_kwargs["base_url"] = settings.LLM_API_BASE

                self.client = AsyncOpenAI(**client_kwargs)
                logger.info(
                    f"LLM服务初始化成功, model={self.model}, "
                    f"base_url={settings.LLM_API_BASE}, "
                    f"read_timeout={self.timeout}s"
                )
            else:
                logger.warning("未配置LLM_API_KEY, LLM服务将不可用")

            self._initialized = True

        except Exception as e:
            logger.error(f"LLM服务初始化失败: {e}")

    async def _retry_call(
        self,
        call_name: str,
        fn: Callable[..., Awaitable],
        on_retry: Optional[Callable[[int, int], Awaitable[None]]] = None,
    ):
        """通用重试骨架

        Args:
            call_name: 调用名称（用于日志）
            fn: 异步调用函数，成功时返回结果
            on_retry: 重试回调

        Returns:
            fn 的返回值

        Raises:
            RuntimeError: 全部重试失败后
        """
        self._initialize()
        if not self.client:
            raise RuntimeError("LLM服务未初始化")

        last_error = None
        for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
            try:
                return await fn()
            except Exception as e:
                last_error = e
                is_timeout = _is_timeout_error(e)
                retry_type = "超时" if is_timeout else "失败"
                logger.warning(
                    f"LLM API {call_name}{retry_type} "
                    f"(attempt {attempt}/{RETRY_MAX_ATTEMPTS}): {e}"
                )

                if attempt < RETRY_MAX_ATTEMPTS:
                    if on_retry:
                        try:
                            await on_retry(attempt, RETRY_MAX_ATTEMPTS)
                        except Exception as cb_err:
                            logger.warning(f"重试回调失败: {cb_err}")

                    delay = _calculate_retry_delay(attempt, is_timeout)
                    logger.info(f"{delay:.0f}秒后进行第{attempt + 1}次重试...")
                    await asyncio.sleep(delay)

        error_msg = (
            f"LLM API {call_name}失败，{RETRY_MAX_ATTEMPTS}次重试后仍失败: "
            f"{last_error}"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    async def stream_chat(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        on_retry: Optional[Callable[[int, int], Awaitable[None]]] = None,
    ) -> AsyncGenerator[str, None]:
        """流式对话，yield 纯文本 delta（带重试）

        重试安全策略：一旦已 yield 任何数据，不再重试。
        原因：AsyncGenerator yield 后无法撤回，重试会导致前端收到重复内容。
        此时直接抛出异常，由调用方决定如何处理（如重新发起完整会话）。
        """
        self._initialize()

        if not self.client:
            raise RuntimeError("LLM服务未初始化")

        last_error = None
        messages = self._build_messages(system_prompt, user_message)

        for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
            has_yielded = False
            try:
                logger.info(f"开始流式调用LLM, model={self.model}, attempt={attempt}")

                stream = await self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=messages,
                    stream=True,
                )

                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        has_yielded = True
                        yield chunk.choices[0].delta.content

                logger.info("LLM流式调用完成")
                return

            except Exception as e:
                last_error = e
                # 已 yield 数据后不重试 — 避免前端收到重复内容
                if has_yielded:
                    logger.error(
                        "LLM流式调用在已输出数据后失败，不重试（避免重复内容）: %s", e
                    )
                    raise RuntimeError(
                        f"LLM流式调用中途失败（已输出部分内容，无法安全重试）: {e}"
                    ) from e

                is_timeout = _is_timeout_error(e)
                retry_type = "超时" if is_timeout else "失败"
                logger.warning(
                    f"LLM API流式调用{retry_type} "
                    f"(attempt {attempt}/{RETRY_MAX_ATTEMPTS}): {e}"
                )

                if attempt < RETRY_MAX_ATTEMPTS:
                    if on_retry:
                        try:
                            await on_retry(attempt, RETRY_MAX_ATTEMPTS)
                        except Exception as cb_err:
                            logger.warning(f"重试回调失败: {cb_err}")

                    delay = _calculate_retry_delay(attempt, is_timeout)
                    logger.info(f"{delay:.0f}秒后进行第{attempt + 1}次重试...")
                    await asyncio.sleep(delay)

        error_msg = (
            f"LLM API流式调用失败，{RETRY_MAX_ATTEMPTS}次重试后仍失败: "
            f"{last_error}"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
    ) -> str:
        """非流式对话（带重试）"""
        messages = self._build_messages(system_prompt, user_message)

        async def _call():
            logger.info(f"开始调用LLM, model={self.model}")
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=messages,
                stream=False,
            )

            if response.choices and response.choices[0].message.content:
                tokens_used = (
                    response.usage.total_tokens
                    if hasattr(response, "usage") and response.usage
                    else 0
                )
                logger.info(f"LLM调用完成, tokens={tokens_used}")
                return response.choices[0].message.content
            else:
                raise RuntimeError("LLM返回空响应")

        return await self._retry_call("chat", _call)

    async def analyze(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = None,
        max_tokens: int = 4096,
    ) -> dict:
        """分析接口（带重试），返回结构化响应"""
        use_model = model or self.model
        messages = self._build_messages(system_prompt, user_prompt)

        async def _call():
            logger.info(f"开始调用LLM analyze, model={use_model}")
            response = await self.client.chat.completions.create(
                model=use_model,
                max_tokens=max_tokens,
                messages=messages,
                stream=False,
            )

            if response.choices and response.choices[0].message.content:
                tokens_used = (
                    response.usage.total_tokens
                    if hasattr(response, "usage") and response.usage
                    else 0
                )
                logger.info(f"LLM analyze完成, tokens={tokens_used}")
                return {
                    "content": response.choices[0].message.content,
                    "tokens_used": tokens_used,
                }
            else:
                raise RuntimeError("LLM返回空响应")

        return await self._retry_call("analyze", _call)

    @staticmethod
    def _build_messages(
        system_prompt: str,
        user_message: str,
    ) -> List[Dict]:
        """构建 OpenAI 格式消息列表"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        return messages


# 全局单例
_llm_service_instance: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """获取 LLM 服务单例"""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance