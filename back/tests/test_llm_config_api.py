"""LLM 配置 API 测试：管理权限收紧与组级批量更新

权限模型：仅 admin 账号或最早注册的账号（最小 account_id）可管理全局 LLM 配置，
防止任意登录账号改写出站 API 地址窃取病历上下文。
"""
import uuid

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select

from app.api.auth import get_current_user
from app.api.llm_config import get_llm_config_manager_user
from app.main import app
from app.models.admin import LLMConfig
from app.models.user import LoginAccount

from conftest import TestSessionLocal


class FakeEncryptionService:
    def encrypt(self, plaintext):
        return f"enc:{plaintext}" if plaintext else plaintext

    def decrypt(self, ciphertext):
        if ciphertext and ciphertext.startswith("enc:"):
            return ciphertext[4:]
        return ciphertext


SETTINGS_ATTRS = (
    "LLM_API_KEY", "LLM_API_BASE", "LLM_MODEL_NAME", "LLM_TIMEOUT",
)


@pytest.fixture(autouse=True)
def fake_encryption(monkeypatch):
    """替换 Fernet 加密，避免依赖本地 ENCRYPTION_KEY 配置"""
    import app.api.llm_config as llm_config_api
    monkeypatch.setattr(llm_config_api, "encryption_service", FakeEncryptionService())


@pytest.fixture(autouse=True)
def restore_llm_settings():
    """apply_configs 会覆盖 Settings 属性，测试后恢复避免污染其他用例"""
    from app.core.config import settings
    snapshot = {k: getattr(settings, k) for k in SETTINGS_ATTRS}
    yield
    for key, value in snapshot.items():
        setattr(settings, key, value)


async def _override_current_user(account_id, account_type="user"):
    current = LoginAccount(account_id=account_id, account_type=account_type)

    async def _override():
        return current

    app.dependency_overrides[get_current_user] = _override
    return current


def teardown_function():
    app.dependency_overrides.pop(get_current_user, None)


# ===== 权限依赖 =====

class TestLLMConfigManagerPermission:
    async def test_admin_allowed(self, db_session, test_user):
        test_user.account_type = "admin"
        await db_session.flush()
        user = await _override_current_user(test_user.account_id, "admin")

        result = await get_llm_config_manager_user(current_user=user, db=db_session)

        assert result.account_id == test_user.account_id

    async def test_first_account_allowed(self, db_session):
        # 显式插入比现存最小 id 更小的主键，构造"最早注册账号"
        first = LoginAccount(
            account_id=-99999,
            username=f"first_{uuid.uuid4().hex[:8]}",
            password="x",
            account_name="首个账号",
            status="active",
        )
        db_session.add(first)
        await db_session.flush()

        user = await _override_current_user(-99999)
        result = await get_llm_config_manager_user(current_user=user, db=db_session)
        assert result.account_id == -99999

    async def test_regular_account_rejected(self, db_session, test_user):
        user = await _override_current_user(test_user.account_id)

        with pytest.raises(HTTPException) as exc_info:
            await get_llm_config_manager_user(current_user=user, db=db_session)

        assert exc_info.value.status_code == 403
        assert "首个账号" in exc_info.value.detail


# ===== 组级批量更新 =====

@pytest_asyncio.fixture
async def manager_headers(client, test_user, db_session):
    """以 test_user（提权为 admin）身份调用受保护端点"""
    test_user.account_type = "admin"
    await db_session.flush()
    await _override_current_user(test_user.account_id, "admin")
    yield client
    app.dependency_overrides.pop(get_current_user, None)


class TestUpdateGroup:
    async def test_update_creates_and_applies(self, manager_headers, db_session):
        response = await manager_headers.put(
            "/api/v1/llm-configs/group/consultation",
            json={"updates": [
                {"config_key": "consultation_api_base", "config_value": "http://llm.example.com/v1"},
                {"config_key": "consultation_api_key", "config_value": "sk-secret-9999"},
            ]},
        )

        assert response.status_code == 200
        items = {i["config_key"]: i for i in response.json()["items"]}
        assert items["consultation_api_base"]["config_value"] == "http://llm.example.com/v1"
        # secret 掩码展示后4位
        assert items["consultation_api_key"]["config_value"] == "****9999"
        assert all(items[k]["is_active"] for k in items)

        from app.core.config import settings
        assert settings.LLM_API_BASE == "http://llm.example.com/v1"
        assert settings.LLM_API_KEY == "enc:sk-secret-9999"

    async def test_masked_and_blank_values_skipped(self, manager_headers, db_session):
        await manager_headers.put(
            "/api/v1/llm-configs/group/consultation",
            json={"updates": [
                {"config_key": "consultation_api_key", "config_value": "sk-original-0001"},
                {"config_key": "consultation_model_name", "config_value": "glm-5"},
            ]},
        )

        response = await manager_headers.put(
            "/api/v1/llm-configs/group/consultation",
            json={"updates": [
                {"config_key": "consultation_api_key", "config_value": "****0001"},  # 掩码 → 不修改
                {"config_key": "consultation_model_name", "config_value": ""},       # 留空 → 不修改
                {"config_key": "consultation_api_base", "config_value": "http://changed.example.com/v1"},
            ]},
        )

        assert response.status_code == 200
        rows = (await db_session.execute(
            select(LLMConfig).where(LLMConfig.config_group == "consultation")
        )).scalars().all()
        values = {r.config_key: r.config_value for r in rows}
        assert values["consultation_api_key"] == "enc:sk-original-0001"
        assert values["consultation_model_name"] == "glm-5"
        assert values["consultation_api_base"] == "http://changed.example.com/v1"

    async def test_unknown_group_returns_404(self, manager_headers):
        response = await manager_headers.put(
            "/api/v1/llm-configs/group/nonexistent",
            json={"updates": [{"config_key": "whatever", "config_value": "x"}]},
        )
        assert response.status_code == 404

    async def test_mismatched_key_returns_400(self, manager_headers):
        response = await manager_headers.put(
            "/api/v1/llm-configs/group/ocr",
            json={"updates": [{"config_key": "consultation_api_key", "config_value": "x"}]},
        )
        assert response.status_code == 400

    async def test_duplicate_key_returns_400(self, manager_headers):
        response = await manager_headers.put(
            "/api/v1/llm-configs/group/ocr",
            json={"updates": [
                {"config_key": "ocr_api_base", "config_value": "a"},
                {"config_key": "ocr_api_base", "config_value": "b"},
            ]},
        )
        assert response.status_code == 400

    async def test_non_manager_forbidden(self, client, test_user, db_session):
        await _override_current_user(test_user.account_id)  # 非 admin、非首个账号
        response = await client.get("/api/v1/llm-configs")
        assert response.status_code == 403
