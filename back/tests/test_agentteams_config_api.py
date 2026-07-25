import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.api.auth import get_current_user
from app.main import app
from app.models.admin import AgentTeamsIntegrationConfig
from app.models.user import LoginAccount


class FakeEncryptionService:
    def encrypt(self, plaintext):
        return f"enc:{plaintext}" if plaintext else plaintext

    def decrypt(self, ciphertext):
        if ciphertext and ciphertext.startswith("enc:"):
            return ciphertext[4:]
        return ciphertext


@pytest_asyncio.fixture(autouse=True)
async def clean_agentteams_configs(db_session, monkeypatch):
    import app.services.agentteams_config_service as config_service

    monkeypatch.setattr(config_service, "encryption_service", FakeEncryptionService())
    await db_session.execute(delete(AgentTeamsIntegrationConfig))
    await db_session.commit()
    yield
    await db_session.execute(delete(AgentTeamsIntegrationConfig))
    await db_session.commit()


def override_current_user(account_type="user"):
    user = LoginAccount(
        account_id=1 if account_type == "admin" else 2,
        username=f"{account_type}_user",
        password="",
        account_type=account_type,
        status="active",
    )

    async def _override():
        return user

    app.dependency_overrides[get_current_user] = _override


def full_payload(**overrides):
    payload = {
        "enabled": True,
        "base_url": "https://agentteams.example.com/",
        "integration_secret": "secret-1234",
        "upsell": {
            "title": "需要配置 AgentTeams 项目",
            "message": "部署 AgentTeams 后即可使用多 Agent 团队进行虚拟会诊分析。",
            "demo_asset_url": "",
            "cta_label": "了解部署方案",
            "cta_url": "",
        },
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_admin_agentteams_config_requires_admin(client, db_session):
    override_current_user("user")

    response = await client.get("/api/v1/admin/agentteams-config")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_first_save_requires_base_url_and_secret(client, db_session):
    override_current_user("admin")

    missing_secret = await client.put(
        "/api/v1/admin/agentteams-config",
        json=full_payload(integration_secret=""),
    )
    missing_base_url = await client.put(
        "/api/v1/admin/agentteams-config",
        json=full_payload(base_url=""),
    )

    assert missing_secret.status_code == 400
    assert missing_base_url.status_code == 400


@pytest.mark.asyncio
async def test_save_masks_secret_encrypts_storage_and_strips_base_url(client, db_session):
    override_current_user("admin")

    response = await client.put(
        "/api/v1/admin/agentteams-config",
        json=full_payload(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is True
    assert data["enabled"] is True
    assert data["base_url"] == "https://agentteams.example.com"
    assert data["integration_secret"] == "****1234"
    assert data["has_integration_secret"] is True

    result = await db_session.execute(select(AgentTeamsIntegrationConfig))
    config = result.scalar_one()
    assert config.integration_secret == "enc:secret-1234"


@pytest.mark.asyncio
async def test_blank_or_masked_secret_preserves_existing_secret(client, db_session):
    override_current_user("admin")
    first = await client.put(
        "/api/v1/admin/agentteams-config",
        json=full_payload(integration_secret="secret-1234"),
    )
    assert first.status_code == 200

    blank = await client.put(
        "/api/v1/admin/agentteams-config",
        json=full_payload(base_url="https://agentteams.example.com/v2", integration_secret=""),
    )
    masked = await client.put(
        "/api/v1/admin/agentteams-config",
        json=full_payload(base_url="https://agentteams.example.com/v3", integration_secret="****1234"),
    )

    assert blank.status_code == 200
    assert masked.status_code == 200
    result = await db_session.execute(select(AgentTeamsIntegrationConfig))
    config = result.scalar_one()
    assert config.integration_secret == "enc:secret-1234"
    assert masked.json()["base_url"] == "https://agentteams.example.com/v3"


@pytest.mark.asyncio
async def test_upsell_copy_is_configurable(client, db_session):
    override_current_user("admin")
    response = await client.put(
        "/api/v1/admin/agentteams-config",
        json=full_payload(
            upsell={
                "title": "custom title",
                "message": "custom message",
                "demo_asset_url": "https://example.com/custom.gif",
                "cta_label": "custom cta",
                "cta_url": "https://example.com/custom",
            },
        ),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["upsell"]["title"] == "custom title"
    assert data["upsell"]["message"] == "custom message"
    assert data["upsell"]["demo_asset_url"] == "https://example.com/custom.gif"
    assert data["upsell"]["cta_label"] == "custom cta"
    assert data["upsell"]["cta_url"] == "https://example.com/custom"


@pytest.mark.asyncio
async def test_availability_returns_unconfigured_for_logged_in_user(client, db_session):
    override_current_user("user")

    response = await client.get("/api/v1/consultation/agentteams/availability")

    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is False
    assert data["enabled"] is False
    assert data["capacity"] is None
    assert "integration_secret" not in data


@pytest.mark.asyncio
async def test_availability_returns_configured_disabled(client, db_session):
    override_current_user("admin")
    saved = await client.put(
        "/api/v1/admin/agentteams-config",
        json=full_payload(enabled=False),
    )
    assert saved.status_code == 200

    override_current_user("user")
    response = await client.get("/api/v1/consultation/agentteams/availability")

    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is True
    assert data["enabled"] is False
    assert data["capacity"] is None
    assert "integration_secret" not in data


@pytest.mark.asyncio
async def test_availability_returns_configured_enabled(client, db_session):
    override_current_user("admin")
    saved = await client.put(
        "/api/v1/admin/agentteams-config",
        json=full_payload(enabled=True),
    )
    assert saved.status_code == 200

    override_current_user("user")
    response = await client.get("/api/v1/consultation/agentteams/availability")

    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is True
    assert data["enabled"] is True
    assert data["base_url"] == "https://agentteams.example.com"
    assert data["upsell"]["demo_asset_url"] == ""
    assert data["upsell"]["cta_url"] == "https://github.com/nickzhang1102/oncopath"
    assert data["capacity"] is None
    assert data["upsell"]["title"]
    assert "integration_secret" not in data
