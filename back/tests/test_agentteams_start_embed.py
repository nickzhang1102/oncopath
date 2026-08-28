import json
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
import httpx
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.api.auth import get_current_admin_user, get_current_user
from app.main import app
from app.models.admin import AgentTeamsIntegrationConfig
from app.models.conversation import ConsultationExternalSession, Conversation, LeaderSession
from app.models.agentteams_launch_intent import (
    AgentTeamsLaunchIntent,
    AgentTeamsLaunchIntentAudit,
)
from app.models.patient import Patient
from app.models.prompt import PromptConfig
from app.models.user import LoginAccount
from app.services.consultation.medical_prompt_builder import MedicalPromptBuilder
from app.services import agentteams_contract as contract
from app.services.agentteams_start_service import AgentTeamsStartService
from app.services.agentteams_launch_intent_service import AgentTeamsLaunchIntentService
from app.utils.time_utils import get_utc_now
from conftest import TestSessionLocal


LAUNCH_REQUEST_ID = "12345678-1234-4234-8234-123456789abc"


class FakeEncryptionService:
    def encrypt(self, plaintext):
        return f"enc:{plaintext}" if plaintext else plaintext

    def decrypt(self, ciphertext):
        if ciphertext and ciphertext.startswith("enc:"):
            return ciphertext[4:]
        return ciphertext


@pytest.mark.parametrize(
    ("agentteams_error", "expected_status", "expected_error", "expected_message"),
    [
        ("invalid_integration_key", 502, "agentteams_invalid_integration_key", "AgentTeams 集成密钥无效"),
        ("invalid_payload", 400, "agentteams_payload_rejected", "AgentTeams 拒绝了本次请求载荷"),
        ("integration_client_not_found", 503, "agentteams_invalid_client_key", "AgentTeams 部署未注册该集成客户端"),
        ("service_account_not_configured", 403, "agentteams_service_account_not_configured", "AgentTeams 服务账户未配置"),
        ("integration_disabled", 403, "agentteams_integration_disabled", "AgentTeams 集成未启用"),
        ("integration_capability_disabled", 403, "agentteams_integration_disabled", "AgentTeams 集成能力未启用"),
        ("unsupported_version", 426, "agentteams_unsupported_version", "AgentTeams 版本不兼容"),
        ("idempotency_conflict", 409, "agentteams_idempotency_conflict", "该启动标识已用于其他会诊，请重新发起"),
    ],
)
def test_agentteams_error_mapping_returns_stable_safe_detail(
    agentteams_error, expected_status, expected_error, expected_message
):
    response = httpx.Response(
        status_code=500,
        json={
            "detail": {
                "error": agentteams_error,
                "message": "raw internal http://agentteams.internal traceback secret",
            }
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        AgentTeamsStartService._raise_agentteams_error(response)

    assert exc_info.value.status_code == expected_status
    assert exc_info.value.detail == {
        "error": expected_error,
        "message": expected_message,
    }
    assert "agentteams.internal" not in str(exc_info.value.detail)


def test_agentteams_unknown_error_mapping_uses_safe_unavailable_detail():
    response = httpx.Response(
        status_code=500,
        json={
            "detail": {
                "error": "database_traceback",
                "message": "raw internal http://agentteams.internal traceback secret",
            }
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        AgentTeamsStartService._raise_agentteams_error(response)

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == {
        "error": "agentteams_unavailable",
        "message": "AgentTeams 服务暂时不可用",
    }
    assert "agentteams.internal" not in str(exc_info.value.detail)


def test_relative_agentteams_api_base_uses_internal_origin(monkeypatch):
    monkeypatch.setattr(
        "app.services.agentteams_start_service.settings.AGENTTEAMS_INTERNAL_ORIGIN",
        "http://frontend",
    )
    service = AgentTeamsStartService(db=None)

    assert service._build_agentteams_api_base("/agentteams") == "http://frontend/agentteams"


def test_integration_launch_urls_target_v1_contract(monkeypatch):
    monkeypatch.setattr(
        "app.services.agentteams_start_service.settings.AGENTTEAMS_INTERNAL_ORIGIN",
        "http://frontend",
    )
    service = AgentTeamsStartService(db=None)

    assert (
        service._integration_launch_url("/agentteams")
        == "http://frontend/agentteams/api/integrations/v1/agentteams/consultation-launches"
    )
    assert (
        service._integration_launch_status_url("https://at.example.com", "req-1")
        == "https://at.example.com/api/integrations/v1/agentteams/consultation-launches/req-1"
    )


def test_relative_agentteams_api_base_rejects_missing_internal_origin(monkeypatch):
    monkeypatch.setattr(
        "app.services.agentteams_start_service.settings.AGENTTEAMS_INTERNAL_ORIGIN",
        "",
    )
    service = AgentTeamsStartService(db=None)

    with pytest.raises(HTTPException) as exc_info:
        service._build_agentteams_api_base("/agentteams")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["error"] == "agentteams_not_configured"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field",
    ["title", "user_ref", "subject_ref", "conversation_ref"],
)
async def test_validate_launch_payload_rejects_overlong_fields_without_remote_call(
    monkeypatch, field
):
    """发送前预校验应在本地拦截超限字段，不把请求送到远端换 400。"""
    fetched = []

    async def fake_capabilities(base_url, integration_secret, client_key):
        fetched.append(base_url)
        return None  # 探测失败时按 DEFAULT_LIMITS 兜底

    monkeypatch.setattr(contract, "fetch_agentteams_capabilities", fake_capabilities)

    payload = {
        "user_ref": "oncopath:1",
        "subject_ref": "42",
        "conversation_ref": "9",
        "title": "病情分析",
        "message": "会诊材料",
    }
    limits = contract.DEFAULT_LIMITS
    limit_key = "title_max_length" if field == "title" else "ref_max_length"
    payload[field] = "x" * (int(limits[limit_key]) + 1)

    with pytest.raises(HTTPException) as exc_info:
        await contract.validate_launch_payload(
            "/agentteams", "secret", "agentteams", payload, "req-1"
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"] == "agentteams_payload_too_large"
    # 预校验发生在远端探测之后（limits 需要 capabilities），但绝不应发起启动调用
    assert fetched == ["/agentteams"]


@pytest.mark.asyncio
async def test_validate_launch_payload_accepts_contract_compliant_payload(monkeypatch):
    async def fake_capabilities(base_url, integration_secret, client_key):
        return {
            "protocol_version": 1,
            "limits": {"title_max_length": 500, "ref_max_length": 100},
        }

    monkeypatch.setattr(contract, "fetch_agentteams_capabilities", fake_capabilities)

    await contract.validate_launch_payload(
        "/agentteams",
        "secret",
        "agentteams",
        {
            "user_ref": "oncopath:1",
            "subject_ref": "42",
            "conversation_ref": "9",
            "title": "病情分析",
            "message": "会诊材料",
            "metadata": {"created_from": "oncopath"},
        },
        "req-1",
    )


@pytest_asyncio.fixture(autouse=True)
async def clean_agentteams_start_data(db_session, monkeypatch):
    import app.services.agentteams_config_service as config_service

    monkeypatch.setattr(config_service, "encryption_service", FakeEncryptionService())
    await db_session.execute(delete(AgentTeamsLaunchIntentAudit))
    await db_session.execute(delete(ConsultationExternalSession))
    await db_session.execute(delete(LeaderSession))
    await db_session.execute(delete(Conversation))
    await db_session.execute(delete(PromptConfig))
    await db_session.execute(delete(AgentTeamsIntegrationConfig))
    await db_session.commit()
    yield
    await db_session.rollback()
    await db_session.execute(delete(AgentTeamsLaunchIntentAudit))
    await db_session.execute(delete(ConsultationExternalSession))
    await db_session.execute(delete(LeaderSession))
    await db_session.execute(delete(Conversation))
    await db_session.execute(delete(PromptConfig))
    await db_session.execute(delete(AgentTeamsIntegrationConfig))
    await db_session.commit()


@pytest_asyncio.fixture
async def patient(db_session, test_user):
    patient = Patient(
        account_id=test_user.account_id,
        patient_name="测试患者",
        gender="unknown",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest_asyncio.fixture
async def current_user_override(test_user):
    current_user = LoginAccount(account_id=test_user.account_id)

    async def _override():
        return current_user

    app.dependency_overrides[get_current_user] = _override
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def admin_user_override(test_user):
    async def _override():
        return test_user

    app.dependency_overrides[get_current_admin_user] = _override
    yield
    app.dependency_overrides.pop(get_current_admin_user, None)


async def save_enabled_config(db_session, base_url="https://agentteams.example.com"):
    config = AgentTeamsIntegrationConfig(
        base_url=base_url,
        integration_secret="enc:secret-1234",
        enabled=True,
    )
    db_session.add(config)
    await db_session.commit()
    return config


def patch_prompt(monkeypatch, prompt="患者资料 prompt"):
    async def fake_build(self, patient_id, db, user_message=None, prompt_config=None):
        return prompt

    monkeypatch.setattr(MedicalPromptBuilder, "build_consultation_prompt", fake_build)


def patch_launch_success(monkeypatch, calls):
    async def fake_launch(self, base_url, integration_secret, request_id, payload):
        calls.append(
            {
                "base_url": base_url,
                "integration_secret": integration_secret,
                "request_id": request_id,
                "payload": payload,
            }
        )
        return {
            "agentteams_conversation_id": 1001,
            "agentteams_share_token": "share-token",
            "agentteams_session_id": 2001,
            "embed_token": "embed-token",
            "embed_path": "/embed/conversation/embed-token",
            "status": "created",
        }

    monkeypatch.setattr(AgentTeamsStartService, "_call_agentteams_launch", fake_launch)


@pytest.mark.asyncio
async def test_agentteams_start_creates_mapping_and_returns_embed_url(
    client, db_session, current_user_override, patient, monkeypatch
):
    await save_enabled_config(db_session)
    patch_prompt(monkeypatch)
    calls = []
    patch_launch_success(monkeypatch, calls)

    response = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id, "request_id": LAUNCH_REQUEST_ID},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "agentteams"
    assert data["external_conversation_id"] == "1001"
    assert data["external_session_id"] == "2001"
    assert data["external_share_token"] == "share-token"
    assert data["embed_url"] == "https://agentteams.example.com/embed/conversation/embed-token"

    result = await db_session.execute(select(ConsultationExternalSession))
    mapping = result.scalar_one()
    assert mapping.conversation_id == data["conversation_id"]
    assert mapping.provider == "agentteams"

    intent = (await db_session.execute(select(AgentTeamsLaunchIntent))).scalar_one()
    assert intent.status == "accepted"
    assert intent.payload_ciphertext is None
    assert intent.payload_purged_at is not None

    assert calls[0]["integration_secret"] == "secret-1234"
    assert calls[0]["request_id"] == f"oncopath-launch-{LAUNCH_REQUEST_ID}"
    assert mapping.launch_request_id == LAUNCH_REQUEST_ID
    assert calls[0]["payload"]["user_ref"] == f"oncopath:{patient.account_id}"
    assert calls[0]["payload"]["subject_ref"] == str(patient.patient_id)
    assert calls[0]["payload"]["conversation_ref"] == str(data["conversation_id"])
    assert calls[0]["payload"]["title"] == f"prompt-#{data['conversation_id']}"
    assert calls[0]["payload"]["title"] != "虚拟会诊"
    assert len(calls[0]["payload"]["title"]) <= AgentTeamsStartService.MAX_TITLE_LENGTH
    assert calls[0]["payload"]["message"] == "患者资料 prompt"
    assert calls[0]["payload"]["message"] not in calls[0]["payload"]["title"]
    assert calls[0]["payload"]["locale"] == "zh-CN"

    conversation_result = await db_session.execute(
        select(Conversation).where(Conversation.id == data["conversation_id"])
    )
    assert conversation_result.scalar_one().title == calls[0]["payload"]["title"]

    session_result = await db_session.execute(select(LeaderSession))
    assert session_result.scalars().all() == []


@pytest.mark.asyncio
async def test_agentteams_start_reuses_request_id_after_lost_success_response(
    client, db_session, current_user_override, patient, monkeypatch
):
    await save_enabled_config(db_session)
    patch_prompt(monkeypatch)
    launch_calls = []
    remote_result = {
        "agentteams_conversation_id": 1001,
        "agentteams_share_token": "share-token",
        "agentteams_session_id": 2001,
        "embed_path": "/embed/conversation/embed-token",
        "status": "created",
    }

    async def fake_launch(self, base_url, integration_secret, request_id, payload):
        launch_calls.append({"request_id": request_id, "payload": payload})
        raise HTTPException(
            status_code=502,
            detail={"error": "agentteams_unavailable", "message": "response lost"},
        )

    async def fake_status(self, base_url, integration_secret, request_id):
        return {
            "found": True,
            "request_id": request_id,
            "status": "created",
            "agentteams_conversation_id": 1001,
            "agentteams_session_id": 2001,
            "conversation_ref": "remote-shell",
            "error_code": None,
        }

    monkeypatch.setattr(AgentTeamsStartService, "_call_agentteams_launch", fake_launch)
    monkeypatch.setattr(AgentTeamsStartService, "_call_agentteams_launch_status", fake_status)
    payload = {"patient_id": patient.patient_id, "request_id": LAUNCH_REQUEST_ID}
    first = await client.post("/api/v1/consultation/agentteams/start", json=payload)
    assert first.status_code == 202
    assert first.json()["launch_status"] == "confirming"
    assert len((await db_session.execute(select(Conversation))).scalars().all()) == 1
    intent = (await db_session.execute(select(AgentTeamsLaunchIntent))).scalar_one()
    assert intent.status == "confirming"

    second = await client.post("/api/v1/consultation/agentteams/start", json=payload)
    assert second.status_code == 202
    assert second.json()["launch_status"] == "manual_review"
    assert second.json()["error"] == "agentteams_embed_unavailable"
    assert [call["request_id"] for call in launch_calls] == [
        f"oncopath-launch-{LAUNCH_REQUEST_ID}",
    ]
    assert len((await db_session.execute(select(Conversation))).scalars().all()) == 1
    assert (await db_session.execute(select(ConsultationExternalSession))).scalars().all() == []


@pytest.mark.asyncio
async def test_new_request_id_does_not_reuse_accepted_running_consultation(
    client, db_session, current_user_override, patient, test_user, monkeypatch
):
    """Accepted launch state is terminal; a later launch gets its own intent."""
    await save_enabled_config(db_session)
    patch_prompt(monkeypatch)
    launch_calls = []
    patch_launch_success(monkeypatch, launch_calls)

    old_conversation = Conversation(
        user_id=test_user.account_id,
        patient_id=patient.patient_id,
        title="旧 AgentTeams 会诊",
        share_token="old-accepted-token",
        status="analyzing",
        category="medical",
    )
    db_session.add(old_conversation)
    await db_session.flush()
    db_session.add(
        AgentTeamsLaunchIntent(
            request_id=LAUNCH_REQUEST_ID,
            conversation_id=old_conversation.id,
            account_id=test_user.account_id,
            patient_id=patient.patient_id,
            status="accepted",
            payload_ciphertext="enc:{}",
            payload_hash="0" * 64,
        )
    )
    db_session.add(
        ConsultationExternalSession(
            conversation_id=old_conversation.id,
            provider="agentteams",
            external_conversation_id="old-remote-conversation",
            external_session_id="old-remote-session",
            external_share_token="old-share-token",
            embed_url="https://agentteams.example.com/embed/old-token",
            status="running",
        )
    )
    await db_session.commit()

    new_request_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    response = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id, "request_id": new_request_id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["launch_status"] == "accepted"
    assert data["request_id"] == new_request_id
    assert data["conversation_id"] != old_conversation.id
    assert [call["request_id"] for call in launch_calls] == [
        f"oncopath-launch-{new_request_id}",
    ]

    intents = (
        await db_session.execute(
            select(AgentTeamsLaunchIntent).order_by(AgentTeamsLaunchIntent.created_at.asc())
        )
    ).scalars().all()
    assert {intent.request_id for intent in intents} == {
        LAUNCH_REQUEST_ID,
        new_request_id,
    }


@pytest.mark.asyncio
async def test_agentteams_start_converges_to_concurrent_request_winner(
    client, db_session, current_user_override, patient, test_user, monkeypatch
):
    await save_enabled_config(db_session)
    patch_prompt(monkeypatch)
    winner_conversation = Conversation(
        user_id=test_user.account_id,
        patient_id=patient.patient_id,
        title="并发 winner",
        status="analyzing",
        category="medical",
    )
    db_session.add(winner_conversation)
    await db_session.commit()
    await db_session.refresh(winner_conversation)
    winner_conversation_id = winner_conversation.id

    async def fake_launch(self, base_url, integration_secret, request_id, payload):
        async with TestSessionLocal() as winner_session:
            winner_session.add(ConsultationExternalSession(
                conversation_id=winner_conversation_id,
                provider=AgentTeamsStartService.PROVIDER,
                launch_request_id=LAUNCH_REQUEST_ID,
                external_conversation_id="1001",
                external_session_id="2001",
                embed_url="https://agentteams.example.com/embed/conversation/winner-token",
                status="created",
            ))
            await winner_session.commit()
        return {
            "agentteams_conversation_id": 1001,
            "agentteams_session_id": 2001,
            "embed_path": "/embed/conversation/loser-token",
            "status": "created",
        }

    monkeypatch.setattr(AgentTeamsStartService, "_call_agentteams_launch", fake_launch)

    response = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id, "request_id": LAUNCH_REQUEST_ID},
    )

    assert response.status_code == 200
    assert response.json()["conversation_id"] == winner_conversation_id
    assert response.json()["embed_url"].endswith("/winner-token")
    conversations = (await db_session.execute(select(Conversation))).scalars().all()
    mappings = (
        await db_session.execute(select(ConsultationExternalSession))
    ).scalars().all()
    assert [conversation.id for conversation in conversations] == [winner_conversation_id]
    assert len(mappings) == 1


@pytest.mark.asyncio
async def test_agentteams_new_start_requires_stable_request_id(
    client, current_user_override, patient
):
    response = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_agentteams_start_rejects_mismatched_request_and_conversation_ids(
    client, db_session, current_user_override, patient, monkeypatch
):
    await save_enabled_config(db_session)
    patch_prompt(monkeypatch)
    patch_launch_success(monkeypatch, [])

    started = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id, "request_id": LAUNCH_REQUEST_ID},
    )
    assert started.status_code == 200
    conversation_id = started.json()["conversation_id"]

    wrong_conversation = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={
            "patient_id": patient.patient_id,
            "conversation_id": conversation_id + 999,
            "request_id": LAUNCH_REQUEST_ID,
        },
    )
    assert wrong_conversation.status_code == 409
    assert wrong_conversation.json()["detail"]["error"] == "agentteams_idempotency_conflict"

    wrong_request = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={
            "patient_id": patient.patient_id,
            "conversation_id": conversation_id,
            "request_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        },
    )
    assert wrong_request.status_code == 409
    assert wrong_request.json()["detail"]["error"] == "agentteams_idempotency_conflict"


def test_conversation_title_is_bounded_and_rejects_ciphertext_as_label():
    conversation = Conversation(id=321, created_at=datetime(2026, 8, 11, 12, 17))

    title = AgentTeamsStartService._build_conversation_title("姓名：gAAAAencrypted-name", conversation)

    assert title == "病情分析-#321"
    assert len(title) <= AgentTeamsStartService.MAX_TITLE_LENGTH


def test_conversation_title_adds_analysis_suffix_to_short_chinese_topic():
    conversation = Conversation(id=21, created_at=datetime(2026, 8, 11, 12, 17))

    title = AgentTeamsStartService._build_conversation_title(
        "诊断：胰腺癌肝转移", conversation
    )

    assert title == "胰腺癌肝转移病情分析-#21"


def test_conversation_title_keeps_suffix_when_topic_exceeds_summary_budget():
    conversation = Conversation(id=22, created_at=datetime(2026, 8, 11, 12, 17))

    title = AgentTeamsStartService._build_conversation_title(
        "诊断：结直肠癌肝转移", conversation
    )

    assert title == "结直肠癌肝转病情分析-#22"


def test_conversation_titles_are_distinct_for_same_patient_and_minute():
    created_at = datetime(2026, 8, 11, 12, 17)

    first = AgentTeamsStartService._build_conversation_title(
        "患者资料", Conversation(id=321, created_at=created_at)
    )
    second = AgentTeamsStartService._build_conversation_title(
        "患者资料", Conversation(id=322, created_at=created_at)
    )

    assert first == "病情分析-#321"
    assert second == "病情分析-#322"
    assert first != second


def test_conversation_title_preserves_sequence_with_full_summary_budget():
    conversation = Conversation(id=2147483647)

    title = AgentTeamsStartService._build_conversation_title(
        "diagnosisabcdefghijk", conversation
    )

    assert title.endswith("-#2147483647")
    assert len(title) <= AgentTeamsStartService.MAX_TITLE_LENGTH


@pytest.mark.asyncio
async def test_agentteams_start_sends_long_prompt_without_truncation(
    client, db_session, current_user_override, patient, monkeypatch
):
    await save_enabled_config(db_session)
    long_prompt = "BEGIN-PATIENT-CONTEXT\n" + ("X" * 61000) + "\nEND-PATIENT-CONTEXT"
    patch_prompt(monkeypatch, prompt=long_prompt)
    calls = []
    patch_launch_success(monkeypatch, calls)

    response = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id, "request_id": LAUNCH_REQUEST_ID},
    )

    assert response.status_code == 200
    assert calls[0]["payload"]["message"] == long_prompt


@pytest.mark.asyncio
async def test_agentteams_start_uses_saved_prompt_config_without_truncation(
    client, db_session, current_user_override, patient, test_user, monkeypatch
):
    await save_enabled_config(db_session)
    long_context = "BEGIN-SAVED-PROMPT\n" + ("真实病历内容" * 2000) + "\nEND-SAVED-PROMPT"
    diagnostic_requirement = "请逐项给出诊断、分期、治疗建议和注意事项"
    db_session.add(PromptConfig(
        account_id=test_user.account_id,
        patient_id=patient.patient_id,
        time_range_days=365,
        user_content_config=json.dumps([
            {
                "id": 1,
                "name": "完整病历",
                "type": "custom",
                "enabled": True,
                "customText": long_context,
            },
            {
                "id": 18,
                "name": "诊断要求",
                "type": "custom",
                "enabled": True,
                "customText": diagnostic_requirement,
            },
        ], ensure_ascii=False),
    ))
    await db_session.commit()
    calls = []
    patch_launch_success(monkeypatch, calls)

    response = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id, "request_id": LAUNCH_REQUEST_ID},
    )

    assert response.status_code == 200
    sent_prompt = calls[0]["payload"]["message"]
    assert len(sent_prompt) > 1300
    assert long_context in sent_prompt
    assert sent_prompt.endswith(f"诊断要求：\n{diagnostic_requirement}\n")


@pytest.mark.asyncio
async def test_agentteams_start_uses_patient_config_with_legacy_stale_account_id(
    client, db_session, current_user_override, patient, test_user, monkeypatch
):
    await save_enabled_config(db_session)
    legacy_owner = LoginAccount(
        username=f"legacy-prompt-owner-{patient.patient_id}",
        password="unused-test-password",
        account_name="历史配置账号",
        status="active",
    )
    db_session.add(legacy_owner)
    await db_session.flush()
    legacy_text = "LEGACY-SAVED-PROMPT-" + ("完整病历" * 600)
    db_session.add(PromptConfig(
        account_id=legacy_owner.account_id,
        patient_id=patient.patient_id,
        time_range_days=365,
        user_content_config=json.dumps([{
            "id": 1,
            "name": "历史完整病历",
            "type": "custom",
            "enabled": True,
            "customText": legacy_text,
        }], ensure_ascii=False),
    ))
    await db_session.commit()
    calls = []
    patch_launch_success(monkeypatch, calls)

    response = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id, "request_id": LAUNCH_REQUEST_ID},
    )

    assert response.status_code == 200
    assert legacy_text in calls[0]["payload"]["message"]
    assert len(calls[0]["payload"]["message"]) > 1300


@pytest.mark.asyncio
async def test_legacy_local_consultation_endpoints_are_disabled(
    client, db_session, current_user_override, patient
):
    disabled_detail = {
        "error": "local_consultation_disabled",
        "message": "本地虚拟会诊已下线，请使用 AgentTeams 会诊",
    }

    create_response = await client.post(
        "/api/v1/consultation/conversations",
        json={"patient_id": patient.patient_id, "request_id": LAUNCH_REQUEST_ID},
    )
    assert create_response.status_code == 410
    assert create_response.json()["detail"] == disabled_detail

    start_response = await client.post(
        "/api/v1/consultation/start",
        json={"patient_id": patient.patient_id, "conversation_id": None},
    )
    assert start_response.status_code == 410
    assert start_response.json()["detail"] == disabled_detail

    stop_response = await client.post(
        "/api/v1/consultation/stop",
        json={"session_id": 123},
    )
    assert stop_response.status_code == 410

    stop_path_response = await client.post("/api/v1/consultation/session/123/stop")
    assert stop_path_response.status_code == 410

    answer_response = await client.post(
        "/api/v1/consultation/answer-questions",
        json={"session_id": 123, "answers": ["answer"]},
    )
    assert answer_response.status_code == 410

    answer_path_response = await client.post(
        "/api/v1/consultation/session/123/answer",
        json={"answers": ["answer"]},
    )
    assert answer_path_response.status_code == 410

    stream_response = await client.get("/api/v1/consultation/session/123/stream")
    assert stream_response.status_code == 410

    detail_response = await client.get("/api/v1/consultation/session/123")
    assert detail_response.status_code == 410

    session_result = await db_session.execute(select(LeaderSession))
    assert session_result.scalars().all() == []


@pytest.mark.asyncio
async def test_agentteams_external_session_can_be_read_and_deleted(
    client, db_session, current_user_override, patient, monkeypatch
):
    monkeypatch.setattr(
        "app.services.agentteams_start_service.settings.AGENTTEAMS_INTERNAL_ORIGIN",
        "http://frontend",
    )
    await save_enabled_config(db_session, base_url="/agentteams")
    patch_prompt(monkeypatch)
    patch_launch_success(monkeypatch, [])
    started = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id, "request_id": LAUNCH_REQUEST_ID},
    )
    conversation_id = started.json()["conversation_id"]

    restarted = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id, "conversation_id": conversation_id},
    )
    assert restarted.status_code == 200
    assert restarted.json()["embed_url"] == "/agentteams/embed/conversation/embed-token"

    read_response = await client.get(
        f"/api/v1/consultation/agentteams/sessions/{conversation_id}",
        params={"patient_id": patient.patient_id},
    )
    assert read_response.status_code == 200
    assert read_response.json()["embed_url"] == "/agentteams/embed/conversation/embed-token"
    assert read_response.json()["status"] == "created"

    result = await db_session.execute(select(ConsultationExternalSession))
    mapping = result.scalar_one()
    assert mapping.embed_url == "/agentteams/embed/conversation/embed-token"

    deleted = await client.delete(
        f"/api/v1/consultation/conversations/{conversation_id}",
    )
    assert deleted.status_code == 200

    result = await db_session.execute(select(ConsultationExternalSession))
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_agentteams_start_rejects_non_owned_patient_with_403(
    client, db_session, current_user_override, test_user
):
    await save_enabled_config(db_session)
    other_owner = LoginAccount(
        username="agentteams-other-owner",
        password="test-password",
        account_name="其他用户",
        status="active",
    )
    db_session.add(other_owner)
    await db_session.flush()
    other_patient = Patient(
        account_id=other_owner.account_id,
        patient_name="其他患者",
        gender="unknown",
    )
    db_session.add(other_patient)
    await db_session.commit()

    response = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": other_patient.patient_id, "request_id": LAUNCH_REQUEST_ID},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "无权访问该患者"


@pytest.mark.asyncio
async def test_agentteams_restart_refreshes_legacy_title_without_renew(
    client, db_session, current_user_override, patient, test_user, monkeypatch
):
    await save_enabled_config(db_session)
    patch_prompt(monkeypatch, "诊断：胰腺癌肝转移")
    conversation = Conversation(
        user_id=test_user.account_id,
        patient_id=patient.patient_id,
        title="测试患者 · 2026-08-11 · 会诊#321",
        status="completed",
        category="medical",
    )
    db_session.add(conversation)
    await db_session.flush()
    mapping = ConsultationExternalSession(
        conversation_id=conversation.id,
        provider=AgentTeamsStartService.PROVIDER,
        external_conversation_id="1001",
        external_session_id="2001",
        embed_url="https://agentteams.example.com/embed/conversation/token",
        status="completed",
    )
    db_session.add(mapping)
    await db_session.commit()
    response = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={
            "patient_id": patient.patient_id,
            "conversation_id": conversation.id,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    await db_session.refresh(conversation)
    await db_session.refresh(mapping)
    assert conversation.title == f"胰腺癌肝转移病情分析-#{conversation.id}"
    assert mapping.status == "completed"
    assert response.json()["embed_url"] == "https://agentteams.example.com/embed/conversation/token"


@pytest.mark.asyncio
async def test_agentteams_start_unconfigured_does_not_create_conversation(
    client, db_session, current_user_override, patient
):
    response = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id, "request_id": LAUNCH_REQUEST_ID},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "agentteams_not_configured"

    result = await db_session.execute(select(Conversation))
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_agentteams_payload_error_rejects_intent_without_mapping(
    client, db_session, current_user_override, patient, monkeypatch
):
    await save_enabled_config(db_session)
    patch_prompt(monkeypatch)

    async def fake_launch_error(self, base_url, integration_secret, request_id, payload):
        # 与真实链路一致：_raise_agentteams_error 已把远端码映射为产品化错误码
        raise HTTPException(
            status_code=400,
            detail={"error": "agentteams_payload_rejected", "message": "AgentTeams 拒绝了本次请求载荷"},
        )

    monkeypatch.setattr(AgentTeamsStartService, "_call_agentteams_launch", fake_launch_error)

    response = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id, "request_id": LAUNCH_REQUEST_ID},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "agentteams_payload_rejected"

    conversations = await db_session.execute(select(Conversation))
    mappings = await db_session.execute(select(ConsultationExternalSession))
    conversation = conversations.scalar_one()
    assert conversation.status == "error"
    assert mappings.scalars().all() == []
    intent = (await db_session.execute(select(AgentTeamsLaunchIntent))).scalar_one()
    assert intent.status == "rejected"
    assert intent.last_error_status == 400
    assert intent.last_error_code == "agentteams_payload_rejected"


@pytest.mark.asyncio
async def test_agentteams_worker_backoff_and_manual_review_never_reposts_launch(
    client, db_session, current_user_override, patient, monkeypatch
):
    await save_enabled_config(db_session)
    patch_prompt(monkeypatch)
    launch_calls = []
    status_calls = []

    async def fake_launch(self, base_url, integration_secret, request_id, payload):
        launch_calls.append(request_id)
        raise HTTPException(
            status_code=502,
            detail={"error": "agentteams_unavailable", "message": "response lost"},
        )

    async def fake_status(self, base_url, integration_secret, request_id):
        status_calls.append(request_id)
        raise HTTPException(
            status_code=502,
            detail={"error": "agentteams_unavailable", "message": "still unavailable"},
        )

    monkeypatch.setattr(AgentTeamsStartService, "_call_agentteams_launch", fake_launch)
    monkeypatch.setattr(AgentTeamsStartService, "_call_agentteams_launch_status", fake_status)

    response = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id, "request_id": LAUNCH_REQUEST_ID},
    )
    assert response.status_code == 202
    assert launch_calls == [f"oncopath-launch-{LAUNCH_REQUEST_ID}"]

    intent = (await db_session.execute(select(AgentTeamsLaunchIntent))).scalar_one()
    assert intent.status == "confirming"
    assert intent.attempt_count == 1
    # The worker must honor backoff and do no immediate status call.
    assert await AgentTeamsLaunchIntentService(db_session).process_available() == 0
    assert status_calls == []

    intent.next_attempt_at = datetime(2000, 1, 1)
    await db_session.commit()
    assert await AgentTeamsLaunchIntentService(db_session).process_available() == 1
    assert status_calls == [f"oncopath-launch-{LAUNCH_REQUEST_ID}"]
    assert launch_calls == [f"oncopath-launch-{LAUNCH_REQUEST_ID}"]

    intent = await db_session.get(AgentTeamsLaunchIntent, intent.id)
    intent.attempt_count = AgentTeamsLaunchIntentService.MAX_RECONCILE_ATTEMPTS - 1
    intent.next_attempt_at = datetime(2000, 1, 1)
    await db_session.commit()
    await AgentTeamsLaunchIntentService(db_session).process_available()
    await db_session.refresh(intent)
    assert intent.status == "manual_review"
    assert intent.last_error_code == "agentteams_reconciliation_exhausted"
    assert launch_calls == [f"oncopath-launch-{LAUNCH_REQUEST_ID}"]

    # A refreshed page or a new client-generated UUID must converge to the
    # same manual-review intent instead of creating a second chargeable launch.
    second = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={
            "patient_id": patient.patient_id,
            "request_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        },
    )
    assert second.status_code == 202
    assert second.json()["launch_status"] == "manual_review"
    assert launch_calls == [f"oncopath-launch-{LAUNCH_REQUEST_ID}"]


@pytest.mark.asyncio
async def test_admin_manual_review_reconcile_is_read_only_and_audited(
    client,
    db_session,
    admin_user_override,
    patient,
    test_user,
    monkeypatch,
):
    await save_enabled_config(db_session)
    conversation = Conversation(
        user_id=test_user.account_id,
        patient_id=patient.patient_id,
        title="待人工复核会诊",
        share_token="manual-reconcile",
        status="error",
        category="medical",
    )
    db_session.add(conversation)
    await db_session.flush()
    intent = AgentTeamsLaunchIntent(
        request_id=LAUNCH_REQUEST_ID,
        conversation_id=conversation.id,
        account_id=test_user.account_id,
        patient_id=patient.patient_id,
        status="manual_review",
        payload_ciphertext="enc:{\"message\":\"patient phi\"}",
        payload_hash="0" * 64,
        attempt_count=AgentTeamsLaunchIntentService.MAX_RECONCILE_ATTEMPTS,
    )
    db_session.add(intent)
    await db_session.commit()
    await db_session.refresh(intent)

    launch_calls = []
    status_calls = []

    async def fail_if_launch_called(self, base_url, integration_secret, request_id, payload):
        launch_calls.append(request_id)
        raise AssertionError("manual review must never call launch POST")

    async def fake_status(self, base_url, integration_secret, request_id):
        status_calls.append(request_id)
        return {
            "found": True,
            "request_id": request_id,
            "status": "running",
            "agentteams_conversation_id": 2001,
            "agentteams_session_id": 3001,
            "error_code": None,
        }

    monkeypatch.setattr(AgentTeamsStartService, "_call_agentteams_launch", fail_if_launch_called)
    monkeypatch.setattr(AgentTeamsStartService, "_call_agentteams_launch_status", fake_status)
    response = await client.post(
        f"/api/v1/admin/agentteams-launch-intents/{intent.id}/reconcile"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["launch_status"] == "manual_review"
    assert data["payload_retained"] is True
    assert data["audits"][0]["action"] == "read_only_reconcile"
    assert data["audits"][0]["before_status"] == "manual_review"
    assert data["audits"][0]["after_status"] == "manual_review"
    assert launch_calls == []
    assert status_calls == [f"oncopath-launch-{LAUNCH_REQUEST_ID}"]
    assert data["last_error_code"] == "agentteams_embed_unavailable"


@pytest.mark.asyncio
async def test_admin_confirmed_not_created_unlocks_new_launch_and_is_audited(
    client,
    db_session,
    current_user_override,
    admin_user_override,
    patient,
    test_user,
    monkeypatch,
):
    await save_enabled_config(db_session)
    patch_prompt(monkeypatch)
    conversation = Conversation(
        user_id=test_user.account_id,
        patient_id=patient.patient_id,
        title="确认未创建会诊",
        share_token="manual-not-created",
        status="error",
        category="medical",
    )
    db_session.add(conversation)
    await db_session.flush()
    intent = AgentTeamsLaunchIntent(
        request_id=LAUNCH_REQUEST_ID,
        conversation_id=conversation.id,
        account_id=test_user.account_id,
        patient_id=patient.patient_id,
        status="manual_review",
        payload_ciphertext="enc:{\"message\":\"patient phi\"}",
        payload_hash="0" * 64,
    )
    db_session.add(intent)
    await db_session.commit()
    await db_session.refresh(intent)

    reason = "已在 AgentTeams 管理端按 request ID 核验，无对应 launch 或计费记录"
    resolved = await client.post(
        f"/api/v1/admin/agentteams-launch-intents/{intent.id}/resolve",
        json={"decision": "confirmed_not_created", "reason": reason},
    )

    assert resolved.status_code == 200
    resolved_data = resolved.json()
    assert resolved_data["launch_status"] == "rejected"
    assert resolved_data["payload_retained"] is False
    assert resolved_data["audits"][0]["action"] == "confirmed_not_created"
    assert resolved_data["audits"][0]["reason"] == reason

    repeated = await client.post(
        f"/api/v1/admin/agentteams-launch-intents/{intent.id}/resolve",
        json={"decision": "confirmed_not_created", "reason": reason},
    )
    assert repeated.status_code == 409
    audits = await db_session.execute(select(AgentTeamsLaunchIntentAudit))
    assert len(audits.scalars().all()) == 1

    launch_calls = []
    patch_launch_success(monkeypatch, launch_calls)
    new_request_id = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    started = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id, "request_id": new_request_id},
    )

    assert started.status_code == 200
    assert started.json()["request_id"] == new_request_id
    assert [call["request_id"] for call in launch_calls] == [
        f"oncopath-launch-{new_request_id}",
    ]


@pytest.mark.asyncio
async def test_admin_cannot_resolve_manual_review_during_active_reconciliation(
    client,
    db_session,
    admin_user_override,
    patient,
    test_user,
):
    conversation = Conversation(
        user_id=test_user.account_id,
        patient_id=patient.patient_id,
        title="正在对账的会诊",
        share_token="active-reconcile",
        status="error",
        category="medical",
    )
    db_session.add(conversation)
    await db_session.flush()
    intent = AgentTeamsLaunchIntent(
        request_id=LAUNCH_REQUEST_ID,
        conversation_id=conversation.id,
        account_id=test_user.account_id,
        patient_id=patient.patient_id,
        status="manual_review",
        payload_ciphertext="enc:{\"message\":\"patient phi\"}",
        payload_hash="0" * 64,
        lease_owner="manual-review-reconciler",
        lease_expires_at=get_utc_now() + timedelta(minutes=1),
    )
    db_session.add(intent)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/admin/agentteams-launch-intents/{intent.id}/resolve",
        json={
            "decision": "confirmed_not_created",
            "reason": "已完成外部核验，但等待当前只读对账结束后再确认",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "agentteams_reconcile_in_progress"
    await db_session.refresh(intent)
    assert intent.status == "manual_review"
    assert intent.payload_ciphertext is not None
    audits = await db_session.execute(select(AgentTeamsLaunchIntentAudit))
    assert audits.scalars().all() == []


@pytest.mark.asyncio
async def test_admin_resolution_rejects_blank_audit_reason(
    client,
    db_session,
    admin_user_override,
    patient,
    test_user,
):
    conversation = Conversation(
        user_id=test_user.account_id,
        patient_id=patient.patient_id,
        title="缺少复核理由的会诊",
        share_token="blank-review-reason",
        status="error",
        category="medical",
    )
    db_session.add(conversation)
    await db_session.flush()
    intent = AgentTeamsLaunchIntent(
        request_id=LAUNCH_REQUEST_ID,
        conversation_id=conversation.id,
        account_id=test_user.account_id,
        patient_id=patient.patient_id,
        status="manual_review",
        payload_ciphertext="enc:{\"message\":\"patient phi\"}",
        payload_hash="0" * 64,
    )
    db_session.add(intent)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/admin/agentteams-launch-intents/{intent.id}/resolve",
        json={"decision": "confirmed_not_created", "reason": "            "},
    )

    assert response.status_code == 422
    await db_session.refresh(intent)
    assert intent.status == "manual_review"
    assert intent.payload_ciphertext is not None
    audits = await db_session.execute(select(AgentTeamsLaunchIntentAudit))
    assert audits.scalars().all() == []


@pytest.mark.asyncio
async def test_stale_reconcile_result_cannot_overwrite_manual_resolution(
    client,
    db_session,
    admin_user_override,
    patient,
    test_user,
):
    conversation = Conversation(
        user_id=test_user.account_id,
        patient_id=patient.patient_id,
        title="已人工处置的会诊",
        share_token="stale-reconcile",
        status="error",
        category="medical",
    )
    db_session.add(conversation)
    await db_session.flush()
    stale_owner = "expired-reconcile-worker"
    intent = AgentTeamsLaunchIntent(
        request_id=LAUNCH_REQUEST_ID,
        conversation_id=conversation.id,
        account_id=test_user.account_id,
        patient_id=patient.patient_id,
        status="manual_review",
        payload_ciphertext="enc:{\"message\":\"patient phi\"}",
        payload_hash="0" * 64,
        lease_owner=stale_owner,
        lease_expires_at=get_utc_now() - timedelta(minutes=1),
    )
    db_session.add(intent)
    await db_session.commit()

    resolved = await client.post(
        f"/api/v1/admin/agentteams-launch-intents/{intent.id}/resolve",
        json={
            "decision": "confirmed_not_created",
            "reason": "已在 AgentTeams 管理端核验该 request ID 确实没有创建记录",
        },
    )
    assert resolved.status_code == 200

    await AgentTeamsLaunchIntentService(db_session)._accept(
        intent,
        {
            "agentteams_conversation_id": "late-remote-conversation",
            "agentteams_session_id": "late-remote-session",
            "agentteams_share_token": "late-share-token",
            "embed_path": "/embed/late-token",
            "status": "running",
        },
        "https://agentteams.example.com",
        lease_owner=stale_owner,
    )

    await db_session.refresh(intent)
    assert intent.status == "rejected"
    assert intent.last_error_code == "agentteams_manually_confirmed_not_created"
    mappings = await db_session.execute(select(ConsultationExternalSession))
    assert mappings.scalars().all() == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("remote_status", "expected_code"),
    [("failed", "agentteams_launch_failed"), ("stopped", "agentteams_launch_stopped")],
)
async def test_agentteams_reconcile_persists_remote_terminal_failure(
    client, db_session, current_user_override, patient, monkeypatch, remote_status, expected_code
):
    await save_enabled_config(db_session)
    patch_prompt(monkeypatch)

    async def fake_launch(self, base_url, integration_secret, request_id, payload):
        raise HTTPException(
            status_code=502,
            detail={"error": "agentteams_unavailable", "message": "response lost"},
        )

    async def fake_status(self, base_url, integration_secret, request_id):
        return {
            "found": True,
            "request_id": request_id,
            "status": remote_status,
            "agentteams_conversation_id": 1001,
            "agentteams_session_id": 2001,
            "error_code": expected_code,
        }

    monkeypatch.setattr(AgentTeamsStartService, "_call_agentteams_launch", fake_launch)
    monkeypatch.setattr(AgentTeamsStartService, "_call_agentteams_launch_status", fake_status)

    response = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id, "request_id": LAUNCH_REQUEST_ID},
    )
    assert response.status_code == 202

    intent = (await db_session.execute(select(AgentTeamsLaunchIntent))).scalar_one()
    intent.next_attempt_at = datetime(2000, 1, 1)
    await db_session.commit()
    assert await AgentTeamsLaunchIntentService(db_session).process_available() == 1
    await db_session.refresh(intent)

    assert intent.status == "rejected"
    assert intent.last_error_status == 409
    assert intent.last_error_code == expected_code
    conversation = await db_session.get(Conversation, intent.conversation_id)
    assert conversation.status == "error"


@pytest.mark.asyncio
async def test_agentteams_reconcile_not_found_stays_ambiguous_and_never_reposts(
    client, db_session, current_user_override, patient, monkeypatch
):
    await save_enabled_config(db_session)
    patch_prompt(monkeypatch)
    launch_calls = []
    status_calls = []

    async def fake_launch(self, base_url, integration_secret, request_id, payload):
        launch_calls.append(request_id)
        raise HTTPException(
            status_code=502,
            detail={"error": "agentteams_unavailable", "message": "response lost"},
        )

    async def fake_status(self, base_url, integration_secret, request_id):
        status_calls.append(request_id)
        return {"found": False, "request_id": request_id, "status": "not_found"}

    monkeypatch.setattr(AgentTeamsStartService, "_call_agentteams_launch", fake_launch)
    monkeypatch.setattr(AgentTeamsStartService, "_call_agentteams_launch_status", fake_status)

    response = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id, "request_id": LAUNCH_REQUEST_ID},
    )
    assert response.status_code == 202

    intent = (await db_session.execute(select(AgentTeamsLaunchIntent))).scalar_one()
    intent.next_attempt_at = datetime(2000, 1, 1)
    await db_session.commit()
    assert await AgentTeamsLaunchIntentService(db_session).process_available() == 1
    await db_session.refresh(intent)

    assert intent.status == "confirming"
    assert intent.last_error_code == "agentteams_launch_not_found"
    assert launch_calls == [f"oncopath-launch-{LAUNCH_REQUEST_ID}"]
    assert status_calls == [f"oncopath-launch-{LAUNCH_REQUEST_ID}"]

    intent.attempt_count = AgentTeamsLaunchIntentService.MAX_RECONCILE_ATTEMPTS - 1
    intent.next_attempt_at = datetime(2000, 1, 1)
    await db_session.commit()
    await AgentTeamsLaunchIntentService(db_session).process_available()
    await db_session.refresh(intent)

    assert intent.status == "manual_review"
    assert launch_calls == [f"oncopath-launch-{LAUNCH_REQUEST_ID}"]

@pytest.mark.asyncio
async def test_conversation_history_only_returns_agentteams_mapped_records(
    client, db_session, current_user_override, patient, test_user
):
    service = AgentTeamsStartService(db_session)
    legacy = Conversation(
        user_id=test_user.account_id,
        patient_id=patient.patient_id,
        title="旧本地会诊",
        share_token="legacy-token",
        status="completed",
        category="medical",
    )
    mapped = Conversation(
        user_id=test_user.account_id,
        patient_id=patient.patient_id,
        title="AgentTeams 会诊",
        share_token="mapped-token",
        status="analyzing",
        category="medical",
    )
    other_patient = Patient(
        account_id=test_user.account_id,
        patient_name="另一个患者",
        gender="unknown",
    )
    db_session.add_all([legacy, mapped, other_patient])
    await db_session.flush()
    other_mapped = Conversation(
        user_id=test_user.account_id,
        patient_id=other_patient.patient_id,
        title="其他患者的 AgentTeams 会诊",
        share_token="other-mapped-token",
        status="completed",
        category="medical",
    )
    db_session.add(other_mapped)
    await db_session.flush()
    db_session.add_all([
        ConsultationExternalSession(
            conversation_id=mapped.id,
            provider=service.PROVIDER,
            external_conversation_id="1001",
            external_session_id="2001",
            external_share_token="share-token",
            embed_url="https://agentteams.example.com/embed/conversation/old-token",
            status="running",
        ),
        ConsultationExternalSession(
            conversation_id=other_mapped.id,
            provider=service.PROVIDER,
            external_conversation_id="1002",
            external_session_id="2002",
            embed_url="https://agentteams.example.com/embed/conversation/other-token",
            status="completed",
        ),
    ])
    await db_session.commit()

    response = await client.get(
        "/api/v1/consultation/conversations",
        params={"patient_id": patient.patient_id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert [item["id"] for item in data["conversations"]] == [mapped.id]
    assert data["conversations"][0]["provider"] == "agentteams"
    assert data["conversations"][0]["external_session_status"] == "running"
    assert data["conversations"][0]["share_token"] == "mapped-token"


@pytest.mark.asyncio
async def test_agentteams_history_requires_patient_context(
    client, current_user_override
):
    response = await client.get(
        "/api/v1/consultation/agentteams/sessions/999999"
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_agentteams_history_rejects_patient_mismatch_without_renew(
    client, db_session, current_user_override, patient, test_user, monkeypatch
):
    other_patient = Patient(
        account_id=test_user.account_id,
        patient_name="另一个患者",
        gender="unknown",
    )
    conversation = Conversation(
        user_id=test_user.account_id,
        patient_id=patient.patient_id,
        title="AgentTeams 会诊",
        status="completed",
        category="medical",
    )
    db_session.add_all([other_patient, conversation])
    await db_session.flush()
    db_session.add(
        ConsultationExternalSession(
            conversation_id=conversation.id,
            provider=AgentTeamsStartService.PROVIDER,
            external_conversation_id="1001",
            external_session_id="2001",
            embed_url="https://agentteams.example.com/embed/conversation/token",
            status="completed",
        )
    )
    await db_session.commit()

    response = await client.get(
        f"/api/v1/consultation/agentteams/sessions/{conversation.id}",
        params={"patient_id": other_patient.patient_id},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_agentteams_status_update_requires_owner_and_persists_status(
    client, db_session, current_user_override, patient, test_user
):
    conversation = Conversation(
        user_id=test_user.account_id,
        patient_id=patient.patient_id,
        title='AgentTeams 会诊',
        status='analyzing',
        category='medical',
    )
    db_session.add(conversation)
    await db_session.flush()
    mapping = ConsultationExternalSession(
        conversation_id=conversation.id,
        provider=AgentTeamsStartService.PROVIDER,
        external_conversation_id='1001',
        external_session_id='2001',
        embed_url='https://agentteams.example.com/embed/conversation/token',
        status='assessing',
    )
    db_session.add(mapping)
    await db_session.commit()

    response = await client.patch(
        f'/api/v1/consultation/agentteams/sessions/{conversation.id}/status',
        params={'patient_id': patient.patient_id},
        json={'status': 'web_search'},
    )
    assert response.status_code == 200
    assert response.json()['status'] == 'web_search'

    await db_session.refresh(mapping)
    assert mapping.status == 'web_search'

    completed = await client.patch(
        f'/api/v1/consultation/agentteams/sessions/{conversation.id}/status',
        params={'patient_id': patient.patient_id},
        json={'status': 'completed'},
    )
    assert completed.status_code == 200
    assert completed.json()['status'] == 'completed'

    stale = await client.patch(
        f'/api/v1/consultation/agentteams/sessions/{conversation.id}/status',
        params={'patient_id': patient.patient_id},
        json={'status': 'monitoring'},
    )
    assert stale.status_code == 200
    assert stale.json()['status'] == 'completed'

    invalid = await client.patch(
        f'/api/v1/consultation/agentteams/sessions/{conversation.id}/status',
        params={'patient_id': patient.patient_id + 999},
        json={'status': 'completed'},
    )
    assert invalid.status_code == 404


@pytest.mark.asyncio
async def test_delete_patient_cleans_agentteams_mapping_and_ignores_legacy_running_session(
    client, db_session, current_user_override, patient, test_user
):
    conversation = Conversation(
        user_id=test_user.account_id,
        patient_id=patient.patient_id,
        title="AgentTeams 会诊",
        share_token="delete-patient-token",
        status="analyzing",
        category="medical",
    )
    db_session.add(conversation)
    await db_session.flush()
    db_session.add(
        ConsultationExternalSession(
            conversation_id=conversation.id,
            provider=AgentTeamsStartService.PROVIDER,
            external_conversation_id="1001",
            external_session_id="2001",
            external_share_token="share-token",
            embed_url="https://agentteams.example.com/embed/conversation/token",
            status="running",
        )
    )
    db_session.add(
        LeaderSession(
            conversation_id=conversation.id,
            patient_id=patient.patient_id,
            user_message="legacy prompt",
            state="assessing",
        )
    )
    await db_session.commit()

    response = await client.delete(f"/api/v1/patients/{patient.patient_id}")

    assert response.status_code == 200

    mappings = await db_session.execute(select(ConsultationExternalSession))
    conversations = await db_session.execute(select(Conversation))
    sessions = await db_session.execute(select(LeaderSession))
    deleted_patient = await db_session.execute(
        select(Patient).where(Patient.patient_id == patient.patient_id)
    )
    assert mappings.scalars().all() == []
    assert conversations.scalars().all() == []
    assert sessions.scalars().all() == []
    assert deleted_patient.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_patient_is_blocked_while_launch_result_is_unresolved(
    client, db_session, current_user_override, patient, test_user
):
    conversation = Conversation(
        user_id=test_user.account_id,
        patient_id=patient.patient_id,
        title="待确认会诊",
        share_token="pending-patient",
        status="analyzing",
        category="medical",
    )
    db_session.add(conversation)
    await db_session.flush()
    db_session.add(AgentTeamsLaunchIntent(
        request_id=LAUNCH_REQUEST_ID,
        conversation_id=conversation.id,
        account_id=test_user.account_id,
        patient_id=patient.patient_id,
        status="confirming",
        payload_ciphertext="enc:{}",
        payload_hash="0" * 64,
    ))
    await db_session.commit()

    response = await client.delete(f"/api/v1/patients/{patient.patient_id}")

    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "agentteams_launch_pending"
    assert await db_session.get(Patient, patient.patient_id) is not None


@pytest.mark.asyncio
async def test_delete_conversation_is_blocked_while_launch_result_is_unresolved(
    client, db_session, current_user_override, patient, test_user
):
    conversation = Conversation(
        user_id=test_user.account_id,
        patient_id=patient.patient_id,
        title="待确认会诊",
        share_token="pending-conv",
        status="analyzing",
        category="medical",
    )
    db_session.add(conversation)
    await db_session.flush()
    db_session.add(AgentTeamsLaunchIntent(
        request_id=LAUNCH_REQUEST_ID,
        conversation_id=conversation.id,
        account_id=test_user.account_id,
        patient_id=patient.patient_id,
        status="manual_review",
        payload_ciphertext="enc:{}",
        payload_hash="0" * 64,
    ))
    await db_session.commit()

    response = await client.delete(f"/api/v1/consultation/conversations/{conversation.id}")

    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "agentteams_launch_pending"
    assert await db_session.get(Conversation, conversation.id) is not None
