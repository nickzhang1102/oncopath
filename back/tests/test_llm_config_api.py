"""LLM 配置 API 测试：管理权限收紧与组级批量更新

权限模型：仅 admin 账号可管理全局 LLM 配置，
防止任意登录账号改写出站 API 地址窃取病历上下文。
"""
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.api.auth import get_current_user
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
    "INTERPRETATION_LLM_API_KEY", "INTERPRETATION_LLM_API_BASE",
    "INTERPRETATION_LLM_MODEL_NAME", "INTERPRETATION_LLM_TIMEOUT",
    "OCR_LLM_API_KEY", "OCR_LLM_API_BASE", "OCR_LLM_MODEL_NAME",
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
    # status 须显式置 active：get_current_admin_user 会校验账号状态
    current = LoginAccount(account_id=account_id, account_type=account_type, status="active")

    async def _override():
        return current

    app.dependency_overrides[get_current_user] = _override
    return current


def teardown_function():
    app.dependency_overrides.pop(get_current_user, None)


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
            "/api/v1/llm-configs/group/interpretation",
            json={"updates": [
                {"config_key": "interpretation_api_base", "config_value": "http://llm.example.com/v1"},
                {"config_key": "interpretation_api_key", "config_value": "sk-secret-9999"},
            ]},
        )

        assert response.status_code == 200
        items = {i["config_key"]: i for i in response.json()["items"]}
        assert items["interpretation_api_base"]["config_value"] == "http://llm.example.com/v1"
        # secret 掩码展示后4位
        assert items["interpretation_api_key"]["config_value"] == "****9999"
        assert all(items[k]["is_active"] for k in items)

        from app.core.config import settings
        assert settings.INTERPRETATION_LLM_API_BASE == "http://llm.example.com/v1"
        assert settings.INTERPRETATION_LLM_API_KEY == "enc:sk-secret-9999"

    async def test_masked_and_blank_values_skipped(self, manager_headers, db_session):
        await manager_headers.put(
            "/api/v1/llm-configs/group/interpretation",
            json={"updates": [
                {"config_key": "interpretation_api_key", "config_value": "sk-original-0001"},
                {"config_key": "interpretation_model_name", "config_value": "glm-5"},
            ]},
        )

        response = await manager_headers.put(
            "/api/v1/llm-configs/group/interpretation",
            json={"updates": [
                {"config_key": "interpretation_api_key", "config_value": "****0001"},  # 掩码 → 不修改
                {"config_key": "interpretation_model_name", "config_value": ""},       # 留空 → 不修改
                {"config_key": "interpretation_api_base", "config_value": "http://changed.example.com/v1"},
            ]},
        )

        assert response.status_code == 200
        rows = (await db_session.execute(
            select(LLMConfig).where(LLMConfig.config_group == "interpretation")
        )).scalars().all()
        values = {r.config_key: r.config_value for r in rows}
        assert values["interpretation_api_key"] == "enc:sk-original-0001"
        assert values["interpretation_model_name"] == "glm-5"
        assert values["interpretation_api_base"] == "http://changed.example.com/v1"

    async def test_unknown_group_returns_404(self, manager_headers):
        response = await manager_headers.put(
            "/api/v1/llm-configs/group/nonexistent",
            json={"updates": [{"config_key": "whatever", "config_value": "x"}]},
        )
        assert response.status_code == 404

    async def test_retired_consultation_group_rejected(self, manager_headers):
        """本地会诊已下线：consultation 组不再可读写"""
        update_resp = await manager_headers.put(
            "/api/v1/llm-configs/group/consultation",
            json={"updates": [{"config_key": "consultation_api_base", "config_value": "x"}]},
        )
        assert update_resp.status_code == 404

        test_resp = await manager_headers.post(
            "/api/v1/llm-configs/test",
            json={"group": "consultation"},
        )
        assert test_resp.status_code == 422  # schema pattern 拒绝

    async def test_mismatched_key_returns_400(self, manager_headers):
        response = await manager_headers.put(
            "/api/v1/llm-configs/group/ocr",
            json={"updates": [{"config_key": "interpretation_api_key", "config_value": "x"}]},
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

    async def test_non_admin_forbidden(self, client, test_user, db_session):
        """非 admin 账号访问 LLM 配置一律 403"""
        await _override_current_user(test_user.account_id)
        response = await client.get("/api/v1/llm-configs")
        assert response.status_code == 403


# ===== 连通性测试（表单即时值覆盖）=====

class _FakeResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code
        self.text = "{}"

    def json(self):
        return {}


class _FakeAsyncClient:
    """返回固定状态码的 httpx.AsyncClient 替身"""

    def __init__(self, status_code=200, **kwargs):
        self._status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url=None, json=None, headers=None):
        return _FakeResponse(self._status_code)


def _clear_llm_settings():
    from app.core.config import settings
    for attr in SETTINGS_ATTRS:
        setattr(settings, attr, "")
    settings.INTERPRETATION_LLM_TIMEOUT = 0
    settings.LLM_API_KEY = ""
    settings.LLM_API_BASE = ""
    settings.LLM_MODEL_NAME = ""


def _install_fake_client(monkeypatch, status_code=200):
    """替换全局 httpx.AsyncClient 为固定响应替身，并捕获最近一次请求参数"""
    import httpx
    captured = {}

    class _CapturingClient(_FakeAsyncClient):
        async def post(self, url=None, json=None, headers=None):
            captured.update({"url": url, "json": json, "headers": headers})
            return _FakeResponse(status_code)

    monkeypatch.setattr(httpx, "AsyncClient", _CapturingClient)
    return captured


class TestLLMConfigTestEndpoint:
    async def test_blank_config_reports_missing_key(self, manager_headers):
        _clear_llm_settings()
        resp = await manager_headers.post("/api/v1/llm-configs/test", json={"group": "interpretation"})
        body = resp.json()
        assert resp.status_code == 200
        assert body["success"] is False
        assert "API Key 未配置" in body["message"]

    async def test_form_override_advances_validation(self, manager_headers):
        """表单即时值无需保存即可参与校验（key 已填 → 推进到地址缺失）"""
        _clear_llm_settings()
        resp = await manager_headers.post(
            "/api/v1/llm-configs/test",
            json={"group": "interpretation", "api_key": "sk-form-0001"},
        )
        assert resp.json()["message"] == "API 地址未配置"

    async def test_form_overrides_used_in_request(self, manager_headers, monkeypatch):
        from app.services.llm_config_service import LLMConfigService

        _clear_llm_settings()
        captured = _install_fake_client(monkeypatch)
        result = await LLMConfigService.test_group(
            "ocr",
            overrides={"api_key": "sk-form-0002", "api_base": "http://form.example.com/v1", "model_name": "glm-5"},
        )

        assert result["success"] is True
        assert captured["json"]["model"] == "glm-5"
        assert captured["headers"]["Authorization"] == "Bearer sk-form-0002"
        assert captured["url"].startswith("http://form.example.com/v1")

    async def test_masked_override_falls_back_to_saved(self, manager_headers, monkeypatch):
        """掩码值视为未提供：请求应携带已保存生效 Key 而非掩码"""
        from app.core.config import settings
        from app.services.llm_config_service import LLMConfigService

        _clear_llm_settings()
        settings.OCR_LLM_API_KEY = "sk-saved-0003"
        settings.OCR_LLM_API_BASE = "http://saved.example.com/v1"
        settings.OCR_LLM_MODEL_NAME = "glm-5"

        captured = _install_fake_client(monkeypatch)
        result = await LLMConfigService.test_group("ocr", overrides={"api_key": "****0003"})

        assert result["success"] is True
        assert captured["headers"]["Authorization"] == "Bearer sk-saved-0003"
        assert captured["url"].startswith("http://saved.example.com/v1")
