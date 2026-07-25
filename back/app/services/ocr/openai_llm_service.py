"""OpenAI兼容LLM服务

用于OCR指标解析，支持任意OpenAI兼容的API服务
"""
import logging
from typing import Optional, Dict, Any
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenAILLMService:
    """OpenAI兼容LLM服务"""

    def __init__(self):
        """初始化服务"""
        self.api_key = settings.OCR_LLM_API_KEY
        self.api_base = settings.OCR_LLM_API_BASE.rstrip('/')
        self.model = settings.OCR_LLM_MODEL_NAME
        self.timeout = settings.OCR_LLM_TIMEOUT
        self.max_tokens = settings.OCR_LLM_MAX_TOKENS
        self._initialized = False

    def _check_initialized(self):
        """检查是否已配置"""
        if not self.api_key:
            raise RuntimeError("未配置OCR_LLM_API_KEY，无法使用LLM解析服务")
        self._initialized = True

    async def analyze(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = None
    ) -> Dict[str, Any]:
        """调用LLM进行分析

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            max_tokens: 最大token数（默认使用配置值）

        Returns:
            dict: 包含 content 和 tokens_used 的字典
        """
        self._check_initialized()

        if not self._initialized:
            raise RuntimeError("LLM服务未初始化")

        # 使用传入的max_tokens或配置值
        use_max_tokens = max_tokens or self.max_tokens

        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": use_max_tokens,
            "temperature": 0.1  # 低温度，更确定性的输出
        }

        try:
            logger.info(f"开始调用OpenAI兼容LLM, model={self.model}, base={self.api_base}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)

            if response.status_code != 200:
                error_text = response.text[:500]
                logger.error(f"LLM API调用失败: status={response.status_code}, response={error_text}")
                raise ValueError(f"LLM API调用失败: {response.status_code} - {error_text}")

            data = response.json()

            # 提取响应内容
            if "choices" not in data or len(data["choices"]) == 0:
                logger.warning("LLM返回空响应")
                raise ValueError("LLM API返回空内容")

            content = data["choices"][0].get("message", {}).get("content", "")
            if not content:
                logger.warning("LLM返回空内容")
                raise ValueError("LLM API返回空内容")

            # 提取token使用量
            tokens_used = data.get("usage", {}).get("total_tokens", 0)

            logger.info(f"LLM调用完成, tokens={tokens_used}, content_length={len(content)}")

            return {
                "content": content,
                "tokens_used": tokens_used
            }

        except httpx.TimeoutException:
            logger.error(f"LLM API调用超时, timeout={self.timeout}s")
            raise ValueError(f"LLM API调用超时 ({self.timeout}s)")
        except httpx.RequestError as e:
            logger.error(f"LLM API网络错误: {e}")
            raise ValueError(f"LLM API网络错误: {e}")
        except Exception as e:
            logger.error(f"LLM调用失败: {e}", exc_info=True)
            raise


# 全局单例
_openai_llm_service_instance: Optional[OpenAILLMService] = None


def get_openai_llm_service() -> OpenAILLMService:
    """获取OpenAI LLM服务单例

    Returns:
        OpenAILLMService 实例
    """
    global _openai_llm_service_instance

    if _openai_llm_service_instance is None:
        _openai_llm_service_instance = OpenAILLMService()

    return _openai_llm_service_instance