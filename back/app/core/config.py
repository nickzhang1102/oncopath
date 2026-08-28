from cryptography.fernet import Fernet
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    APP_NAME: str = "OncoPath"
    APP_VERSION: str = "2.1.0"
    DEBUG: bool = False
    DEBUG_ENABLED: bool = False  # 调试端点开关，生产环境必须为 False

    # 数据库配置 (PostgreSQL)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = "medical_report"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-in-production"

    # 数据加密配置
    ENCRYPTION_KEY: str = ""
    ALLOW_UNENCRYPTED_PHI: bool = False

    @field_validator("ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """校验 ENCRYPTION_KEY 格式（空值由 model_validator 检查）"""
        if v:
            try:
                Fernet(v.encode())
            except Exception:
                raise ValueError(
                    "ENCRYPTION_KEY 格式无效，请使用 Fernet.generate_key() 生成"
                )
        return v

    @model_validator(mode="after")
    def check_encryption_config(self):
        """ENCRYPTION_KEY 为空时必须显式允许未加密 PHI"""
        if not self.ENCRYPTION_KEY and not self.ALLOW_UNENCRYPTED_PHI:
            raise ValueError(
                "ENCRYPTION_KEY 未配置！医疗系统必须加密 PHI 字段。"
                "开发环境可设置 ALLOW_UNENCRYPTED_PHI=true 显式允许。"
            )
        return self

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """校验 SECRET_KEY 不为默认值或空"""
        forbidden = {
            "your-secret-key-change-in-production",
            "your-secret-key-change-in-production-please",
            # .env.example 历史示例值，防止被原样沿用为生产密钥
            "your-super-secret-key-change-this-in-production-must-be-at-least-32-chars",
            "",
        }
        # 占位符提示词拦截（覆盖 .env.example 各版本占位符及其变体）
        if v in forbidden or "必须修改" in v:
            raise ValueError(
                "SECRET_KEY 不能使用默认值或为空，请通过环境变量设置强随机密钥 "
                "(使用 openssl rand -hex 32 生成)"
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY 长度至少 32 个字符")
        return v

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS配置
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # LLM配置 (OpenAI 兼容 API - 用于会诊等)
    LLM_API_KEY: str = ""
    LLM_API_BASE: str = "http://127.0.0.1:3456"
    LLM_MODEL_NAME: str = "glm-5"
    LLM_TIMEOUT: int = 120  # 秒

    # 指标解读专用LLM配置 (缺省回退到 LLM_*)
    INTERPRETATION_LLM_API_KEY: str = ""
    INTERPRETATION_LLM_API_BASE: str = ""
    INTERPRETATION_LLM_MODEL_NAME: str = ""
    INTERPRETATION_LLM_TIMEOUT: int = 0  # 0 表示使用 LLM_TIMEOUT

    @field_validator("INTERPRETATION_LLM_TIMEOUT", mode="before")
    @classmethod
    def validate_interpretation_timeout(cls, v):
        """空字符串转为0，表示回退到 LLM_TIMEOUT"""
        if v == "" or v is None:
            return 0
        return int(v)

    @property
    def interpretation_api_key(self) -> str:
        return self.INTERPRETATION_LLM_API_KEY or self.LLM_API_KEY

    @property
    def interpretation_api_base(self) -> str:
        return self.INTERPRETATION_LLM_API_BASE or self.LLM_API_BASE

    @property
    def interpretation_model_name(self) -> str:
        return self.INTERPRETATION_LLM_MODEL_NAME or self.LLM_MODEL_NAME

    @property
    def interpretation_timeout(self) -> int:
        return self.INTERPRETATION_LLM_TIMEOUT or self.LLM_TIMEOUT

    # 旧版本地会诊的 Web 搜索环境变量，仅用于兼容已有 .env 配置；
    # 当前由 AgentTeams 承接的会诊运行时不会使用这些变量。
    EXA_API_KEY: str = ""
    TAVILY_API_KEY: str = ""

    # OCR专用LLM配置 (OpenAI兼容接口)
    OCR_LLM_API_KEY: str = ""
    OCR_LLM_API_BASE: str = "https://api.openai.com/v1"
    OCR_LLM_MODEL_NAME: str = "gpt-4o"
    OCR_LLM_TIMEOUT: int = 600  # 秒
    OCR_LLM_MAX_TOKENS: int = 64000  # 最大输出token数

    # 匹配配置
    DEFAULT_CONFIDENCE_THRESHOLD: float = 0.85
    HIGH_CONFIDENCE_THRESHOLD: float = 0.90
    LOW_CONFIDENCE_THRESHOLD: float = 0.70

    # Legacy local-consultation environment variables. Accepted during upgrades
    # so existing private .env files do not prevent startup; runtime code does
    # not consume these values.
    CONSULTATION_RECENT_REPORTS_DAYS: int = 60
    CONSULTATION_EXPERT_RECOMMENDATION_COUNT: int = 6
    CONSULTATION_EXPERT_ANALYSIS_TIMEOUT: int = 60
    CONSULTATION_TOTAL_TIMEOUT: int = 3600
    CONSULTATION_MAX_RETRY_ATTEMPTS: int = 3
    CONSULTATION_CACHE_EXPIRE_SECONDS: int = 3600
    EXPERT_TIMEOUT_SECONDS: int = 60
    ENABLE_EXPERT_DISCUSSION: bool = True
    MAX_DISCUSSION_ROUNDS: int = 3
    CONSULTATION_QUESTION_TIMEOUT: int = 300
    CONSULTATION_QUESTION_MAX_ROUNDS: int = 2
    CONSULTATION_HEARTBEAT_INTERVAL: int = 30
    CONSULTATION_HEARTBEAT_TIMEOUT: int = 60

    # AgentTeams 集成配置
    # 当后台 AgentTeams base_url 配置为 /agentteams 这类同站路径时，
    # 后端容器用该 origin 访问当前站点的反代入口。
    AGENTTEAMS_INTERNAL_ORIGIN: str = ""
    # 集成客户端身份（对应 agentTeams integration_clients.client_key）。
    # 默认 agentteams 走兼容客户端；部署多租户时改为已注册的 client_key。
    AGENTTEAMS_CLIENT_KEY: str = "agentteams"

    # 文件存储配置
    STORAGE_TYPE: str = "local"  # local / minio (未来扩展)
    STORAGE_PATH: str = "storage"  # 本地存储根目录

    @property
    def STORAGE_PATH_RESOLVED(self) -> "Path":
        """解析并自动创建存储根目录"""
        from pathlib import Path as _Path
        path = _Path(self.STORAGE_PATH)
        path.mkdir(parents=True, exist_ok=True)
        return path

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )


# 全局配置实例
settings = Settings()
