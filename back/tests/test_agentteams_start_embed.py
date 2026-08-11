import json

import pytest
import pytest_asyncio
import httpx
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.api.auth import get_current_user
from app.main import app
from app.models.admin import AgentTeamsIntegrationConfig
from app.models.conversation import ConsultationExternalSession, Conversation, LeaderSession
from app.models.patient import Patient
from app.models.prompt import PromptConfig
from app.models.user import LoginAccount
from app.services.consultation.medical_prompt_builder import MedicalPromptBuilder
from app.services.agentteams_start_service import AgentTeamsStartService


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
        ("service_account_quota_exceeded", 402, "agentteams_quota_exceeded", "AgentTeams 会诊额度不足"),
        ("service_account_not_configured", 403, "agentteams_service_account_not_configured", "AgentTeams 服务账户未配置"),
        ("integration_disabled", 403, "agentteams_integration_disabled", "AgentTeams 集成未启用"),
        ("unsupported_version", 426, "agentteams_unsupported_version", "AgentTeams 版本不兼容"),
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


@pytest_asyncio.fixture(autouse=True)
async def clean_agentteams_start_data(db_session, monkeypatch):
    import app.services.agentteams_config_service as config_service

    monkeypatch.setattr(config_service, "encryption_service", FakeEncryptionService())
    await db_session.execute(delete(ConsultationExternalSession))
    await db_session.execute(delete(LeaderSession))
    await db_session.execute(delete(Conversation))
    await db_session.execute(delete(PromptConfig))
    await db_session.execute(delete(AgentTeamsIntegrationConfig))
    await db_session.commit()
    yield
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
    async def _override():
        return test_user

    app.dependency_overrides[get_current_user] = _override
    yield
    app.dependency_overrides.pop(get_current_user, None)


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


def patch_embed_renew_success(monkeypatch, calls, embed_token="renewed-token", status="running"):
    async def fake_renew(self, base_url, integration_secret, payload):
        calls.append(
            {
                "base_url": base_url,
                "integration_secret": integration_secret,
                "payload": payload,
            }
        )
        return {
            "agentteams_conversation_id": payload["agentteams_conversation_id"],
            "agentteams_session_id": payload["agentteams_session_id"],
            "embed_token": embed_token,
            "embed_path": f"/embed/conversation/{embed_token}",
            "status": status,
        }

    monkeypatch.setattr(AgentTeamsStartService, "_call_agentteams_embed_renew", fake_renew)


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
        json={"patient_id": patient.patient_id},
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

    assert calls[0]["integration_secret"] == "secret-1234"
    assert calls[0]["request_id"] == f"oncopath-conversation-{data['conversation_id']}"
    assert calls[0]["payload"]["source_conversation_id"] == data["conversation_id"]
    assert calls[0]["payload"]["message"] == "患者资料 prompt"
    assert calls[0]["payload"]["locale"] == "zh-CN"

    session_result = await db_session.execute(select(LeaderSession))
    assert session_result.scalars().all() == []


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
        json={"patient_id": patient.patient_id},
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
        system_prompt="肿瘤多学科会诊",
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
        json={"patient_id": patient.patient_id},
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
        system_prompt="肿瘤多学科会诊",
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
        json={"patient_id": patient.patient_id},
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
        json={"patient_id": patient.patient_id},
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
    renew_calls = []
    patch_embed_renew_success(monkeypatch, renew_calls)

    started = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id},
    )
    conversation_id = started.json()["conversation_id"]

    restarted = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id, "conversation_id": conversation_id},
    )
    assert restarted.status_code == 200
    assert restarted.json()["embed_url"] == "/agentteams/embed/conversation/renewed-token"
    assert renew_calls == [
        {
            "base_url": "/agentteams",
            "integration_secret": "secret-1234",
            "payload": {
                "source_conversation_id": conversation_id,
                "agentteams_conversation_id": 1001,
                "agentteams_session_id": 2001,
            },
        }
    ]

    renew_calls.clear()

    read_response = await client.get(
        f"/api/v1/consultation/agentteams/sessions/{conversation_id}",
        params={"patient_id": patient.patient_id},
    )
    assert read_response.status_code == 200
    assert read_response.json()["embed_url"] == "/agentteams/embed/conversation/renewed-token"
    assert read_response.json()["status"] == "running"
    assert renew_calls == [
        {
            "base_url": "/agentteams",
            "integration_secret": "secret-1234",
            "payload": {
                "source_conversation_id": conversation_id,
                "agentteams_conversation_id": 1001,
                "agentteams_session_id": 2001,
            },
        }
    ]

    result = await db_session.execute(select(ConsultationExternalSession))
    mapping = result.scalar_one()
    assert mapping.embed_url == "/agentteams/embed/conversation/renewed-token"

    deleted = await client.delete(
        f"/api/v1/consultation/conversations/{conversation_id}",
    )
    assert deleted.status_code == 200

    result = await db_session.execute(select(ConsultationExternalSession))
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_agentteams_start_unconfigured_does_not_create_conversation(
    client, db_session, current_user_override, patient
):
    response = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "agentteams_not_configured"

    result = await db_session.execute(select(Conversation))
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_agentteams_capacity_error_rolls_back_local_shell(
    client, db_session, current_user_override, patient, monkeypatch
):
    await save_enabled_config(db_session)
    patch_prompt(monkeypatch)

    async def fake_launch_error(self, base_url, integration_secret, request_id, payload):
        raise HTTPException(
            status_code=402,
            detail={"error": "agentteams_quota_exceeded", "message": "AgentTeams 会诊额度不足"},
        )

    monkeypatch.setattr(AgentTeamsStartService, "_call_agentteams_launch", fake_launch_error)

    response = await client.post(
        "/api/v1/consultation/agentteams/start",
        json={"patient_id": patient.patient_id},
    )

    assert response.status_code == 402
    assert response.json()["detail"]["error"] == "agentteams_quota_exceeded"

    conversations = await db_session.execute(select(Conversation))
    mappings = await db_session.execute(select(ConsultationExternalSession))
    assert conversations.scalars().all() == []
    assert mappings.scalars().all() == []


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
async def test_agentteams_history_rejects_patient_mismatch_before_renew(
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

    renew_calls = []
    patch_embed_renew_success(monkeypatch, renew_calls)
    response = await client.get(
        f"/api/v1/consultation/agentteams/sessions/{conversation.id}",
        params={"patient_id": other_patient.patient_id},
    )

    assert response.status_code == 404
    assert renew_calls == []


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
