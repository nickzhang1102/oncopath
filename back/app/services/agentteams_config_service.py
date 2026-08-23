"""AgentTeams 集成配置服务"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import AgentTeamsIntegrationConfig
from app.core.config import settings
from app.schemas.agentteams import (
    AgentTeamsAvailabilityResponse,
    AgentTeamsConfigResponse,
    AgentTeamsConfigUpdate,
    AgentTeamsUpsell,
)
from app.services.encryption_service import encryption_service


DEFAULT_UPSELL = AgentTeamsUpsell(
    title="需要部署 AgentTeams 项目",
    message=(
        "虚拟会诊由开源的 AgentTeams 项目提供多 Agent 团队分析引擎。"
        "部署 AgentTeams 并在管理后台完成集成配置后即可使用。"
        "点击下方按钮获取 AgentTeams 源码与部署指引。"
    ),
    demo_asset_url="",
    cta_label="获取 AgentTeams（开源自部署）",
    cta_url="https://github.com/nickzhang1102/agentTeams",
)


class AgentTeamsConfigError(ValueError):
    """AgentTeams 配置校验错误"""


@dataclass(frozen=True)
class AgentTeamsRuntimeConfig:
    configured: bool
    enabled: bool
    base_url: str
    integration_secret: str


class AgentTeamsConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_config(self) -> AgentTeamsConfigResponse:
        config = await self._get_config_row()
        return self._to_admin_response(config)

    async def update_config(self, data: AgentTeamsConfigUpdate) -> AgentTeamsConfigResponse:
        base_url = self._normalize_base_url(data.base_url)
        secret = data.integration_secret.strip()
        config = await self._get_config_row()

        if not base_url:
            raise AgentTeamsConfigError("AgentTeams base_url 不能为空")
        if not self._is_valid_base_url(base_url):
            raise AgentTeamsConfigError("AgentTeams base_url 必须以 http://、https:// 或 /agentteams 开头")

        should_keep_secret = self._is_masked_secret(secret) or secret == ""
        if not config and should_keep_secret:
            raise AgentTeamsConfigError("首次保存 AgentTeams 集成配置时 integration_secret 不能为空")

        if not config:
            config = AgentTeamsIntegrationConfig(
                base_url=base_url,
                integration_secret=encryption_service.encrypt(secret),
            )
            self.db.add(config)
        else:
            config.base_url = base_url
            if not should_keep_secret:
                config.integration_secret = encryption_service.encrypt(secret)

        config.enabled = data.enabled
        self._apply_upsell(
            config,
            data.upsell,
            update_existing="upsell" in data.model_fields_set,
        )

        await self.db.commit()
        await self.db.refresh(config)
        return self._to_admin_response(config)

    async def get_availability(self) -> AgentTeamsAvailabilityResponse:
        config = await self._get_config_row()
        admin_response = self._to_admin_response(config)
        enabled = (
            admin_response.configured
            and admin_response.enabled
            and self._has_trusted_api_origin(admin_response.base_url)
        )
        return AgentTeamsAvailabilityResponse(
            configured=admin_response.configured,
            enabled=enabled,
            base_url=admin_response.base_url if admin_response.configured else "",
            capacity=None,
            upsell=admin_response.upsell,
        )

    async def get_runtime_config(self) -> AgentTeamsRuntimeConfig:
        """读取服务端调用 AgentTeams 所需配置。不要把返回值暴露给前端。"""
        config = await self._get_config_row()
        if not config:
            return AgentTeamsRuntimeConfig(
                configured=False,
                enabled=False,
                base_url="",
                integration_secret="",
            )

        secret = self._decrypt_secret(config.integration_secret)
        configured = bool(
            config.base_url
            and secret
            and self._has_trusted_api_origin(config.base_url)
        )
        return AgentTeamsRuntimeConfig(
            configured=configured,
            enabled=configured and bool(config.enabled),
            base_url=config.base_url or "",
            integration_secret=secret,
        )

    async def _get_config_row(self) -> AgentTeamsIntegrationConfig | None:
        result = await self.db.execute(
            select(AgentTeamsIntegrationConfig).order_by(AgentTeamsIntegrationConfig.id).limit(1)
        )
        return result.scalar_one_or_none()

    def _to_admin_response(self, config: AgentTeamsIntegrationConfig | None) -> AgentTeamsConfigResponse:
        if not config:
            return AgentTeamsConfigResponse(
                configured=False,
                enabled=False,
                base_url="",
                integration_secret="",
                has_integration_secret=False,
                upsell=DEFAULT_UPSELL,
                updated_at=None,
            )

        raw_secret = self._decrypt_secret(config.integration_secret)
        has_secret = bool(raw_secret)
        configured = bool(config.base_url and has_secret)
        return AgentTeamsConfigResponse(
            configured=configured,
            enabled=bool(config.enabled),
            base_url=config.base_url or "",
            integration_secret=self._mask_secret_value(raw_secret) if has_secret else "",
            has_integration_secret=has_secret,
            upsell=AgentTeamsUpsell(
                title=config.upsell_title or DEFAULT_UPSELL.title,
                message=config.upsell_message or DEFAULT_UPSELL.message,
                demo_asset_url=config.demo_asset_url or DEFAULT_UPSELL.demo_asset_url,
                cta_label=config.cta_label or DEFAULT_UPSELL.cta_label,
                cta_url=config.cta_url or DEFAULT_UPSELL.cta_url,
            ),
            updated_at=config.updated_at,
        )

    def _apply_upsell(
        self,
        config: AgentTeamsIntegrationConfig,
        upsell: AgentTeamsUpsell,
        update_existing: bool,
    ) -> None:
        if not update_existing and config.id:
            return

        config.upsell_title = upsell.title or DEFAULT_UPSELL.title
        config.upsell_message = upsell.message or DEFAULT_UPSELL.message
        config.demo_asset_url = upsell.demo_asset_url or DEFAULT_UPSELL.demo_asset_url
        config.cta_label = upsell.cta_label or DEFAULT_UPSELL.cta_label
        config.cta_url = upsell.cta_url or DEFAULT_UPSELL.cta_url

    def _decrypt_secret(self, encrypted_secret: str) -> str:
        try:
            return encryption_service.decrypt(encrypted_secret) or ""
        except ValueError:
            return encrypted_secret or ""

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        return (base_url or "").strip().rstrip("/")

    @staticmethod
    def _is_valid_base_url(base_url: str) -> bool:
        return (
            base_url.startswith("http://")
            or base_url.startswith("https://")
            or base_url == "/agentteams"
            or base_url.startswith("/agentteams/")
        )

    @staticmethod
    def _has_trusted_api_origin(base_url: str) -> bool:
        return (
            base_url.startswith("http://")
            or base_url.startswith("https://")
            or bool(settings.AGENTTEAMS_INTERNAL_ORIGIN.strip())
        )

    @staticmethod
    def _is_masked_secret(secret: str) -> bool:
        return secret.startswith("****")

    @staticmethod
    def _mask_secret_value(value: str) -> str:
        if not value or len(value) <= 4:
            return "****"
        return f"****{value[-4:]}"
