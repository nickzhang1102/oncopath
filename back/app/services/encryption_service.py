"""Fernet 对称加密服务 — 用于 PHI 字段静态加密"""
import hashlib
import hmac
import logging
import re
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """患者敏感字段加密/解密服务（延迟初始化）"""

    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._initialized = False

    def _ensure_initialized(self):
        """延迟初始化：首次使用加密/解密时才检查配置。

        注意: 此方法不含 await，在 FastAPI async 端点中单线程执行，
        因此不存在并发竞态。若未来添加 I/O 操作需引入 asyncio.Lock。
        """
        if self._initialized:
            return

        key = settings.ENCRYPTION_KEY
        if not key:
            if not settings.ALLOW_UNENCRYPTED_PHI:
                raise RuntimeError(
                    "ENCRYPTION_KEY 未配置，PHI 字段无法加密！"
                    "开发环境可设置 ALLOW_UNENCRYPTED_PHI=true"
                )
            logger.warning("=" * 60)
            logger.warning("警告：ENCRYPTION_KEY 未配置，PHI 字段将不会加密！")
            logger.warning("此模式仅限开发环境使用，生产环境必须配置加密密钥！")
            logger.warning("=" * 60)
            self._fernet = None
        else:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

        self._initialized = True

    def encrypt(self, plaintext: Optional[str]) -> Optional[str]:
        """加密明文字段"""
        if not plaintext:
            return plaintext
        self._ensure_initialized()
        if not self._fernet:
            return plaintext
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: Optional[str]) -> Optional[str]:
        """解密 PHI；历史明文原样返回，Fernet 验签失败则拒绝降级。"""
        if not ciphertext:
            return ciphertext
        self._ensure_initialized()
        if not self._fernet:
            return ciphertext
        looks_like_fernet = (
            ciphertext.startswith("gAAAA")
            or (len(ciphertext) >= 80 and re.fullmatch(r"[A-Za-z0-9_-]+=*", ciphertext))
        )
        if not looks_like_fernet:
            return ciphertext
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            logger.error("PHI Fernet 密文无法使用当前 ENCRYPTION_KEY 解密")
            raise ValueError(
                "PHI Fernet 密文与当前 ENCRYPTION_KEY 不匹配或密文已损坏"
            ) from exc

    def hash_for_index(self, plaintext: Optional[str]) -> Optional[str]:
        """单向 HMAC-SHA256 哈希，用于身份证查重索引（不可逆）。

        使用 ENCRYPTION_KEY 作为 HMAC 密钥，防止彩虹表攻击。
        若 ENCRYPTION_KEY 未配置（开发环境），回退到带固定盐的 SHA-256。
        """
        if not plaintext:
            return None
        self._ensure_initialized()
        if self._fernet and settings.ENCRYPTION_KEY:
            # 使用 ENCRYPTION_KEY 前 32 字节作为 HMAC 密钥
            key_bytes = settings.ENCRYPTION_KEY.encode() if isinstance(
                settings.ENCRYPTION_KEY, str
            ) else settings.ENCRYPTION_KEY
            return hmac.new(key_bytes, plaintext.encode(), hashlib.sha256).hexdigest()
        # 开发环境回退：使用固定应用盐防止裸 SHA-256
        salted = f"oncopath-dev-salt:{plaintext}"
        return hashlib.sha256(salted.encode()).hexdigest()


encryption_service = EncryptionService()
