"""患者编辑端点测试 — GET /patients/{id}/edit 返回明文敏感字段"""
import sys
import os
import types
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport
from datetime import datetime

# 设置模块路径
_back_dir = os.path.join(os.path.dirname(__file__), "..")
_back_dir = os.path.abspath(_back_dir)

if _back_dir not in sys.path:
    sys.path.insert(0, _back_dir)


@pytest.mark.asyncio
async def test_get_patient_edit_returns_plaintext():
    """GET /patients/{id}/edit 应返回明文敏感字段（非脱敏）"""
    from app.api.patient import router, verify_patient_access

    # 模拟已解密的患者对象
    mock_patient = MagicMock()
    mock_patient.patient_id = 1
    mock_patient.account_id = 100
    mock_patient.patient_name = "张三"  # 明文，非 "张**"
    mock_patient.patient_phone = "13812345678"  # 明文，非 "138****5678"
    mock_patient.gender = "male"
    mock_patient.birth_date = None
    mock_patient.id_card = "110101199001011234"  # 明文，非 "110**********1234"
    mock_patient.emergency_contact = "李四"
    mock_patient.emergency_phone = "13987654321"
    mock_patient.medical_history = None
    mock_patient.allergies = None
    mock_patient.current_medications = None
    mock_patient.notes = None
    mock_patient.is_primary = True
    mock_patient.created_at = datetime(2026, 1, 1, 0, 0, 0)
    mock_patient.updated_at = None

    mock_patient.to_dict.return_value = {
        "patient_id": 1,
        "account_id": 100,
        "patient_name": "张三",
        "patient_phone": "13812345678",
        "gender": "male",
        "birth_date": None,
        "id_card": "110101199001011234",
        "emergency_contact": "李四",
        "emergency_phone": "13987654321",
        "medical_history": None,
        "allergies": None,
        "current_medications": None,
        "notes": None,
        "is_primary": True,
        "created_at": datetime(2026, 1, 1, 0, 0, 0),
        "updated_at": None,
    }

    with patch("app.api.patient.verify_patient_access", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = mock_patient

        from fastapi import FastAPI
        from app.api.auth import get_current_user

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/patients")

        # 模拟认证
        mock_user = MagicMock()
        mock_user.account_id = 100

        app.dependency_overrides[get_current_user] = lambda: mock_user

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/patients/1/edit")

        assert response.status_code == 200
        data = response.json()
        # 明文字段不含脱敏星号
        assert data["patient_name"] == "张三"
        assert "**" not in data["patient_name"]
        assert data["patient_phone"] == "13812345678"
        assert "****" not in data["patient_phone"]
        assert data["id_card"] == "110101199001011234"
        assert "********" not in data["id_card"]


@pytest.mark.asyncio
async def test_get_patient_edit_requires_auth():
    """GET /patients/{id}/edit 需要认证"""
    from fastapi import FastAPI
    from app.api.patient import router
    from app.api.auth import get_current_user
    from fastapi import HTTPException

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/patients")

    # 未认证时抛出 401
    def raise_401():
        raise HTTPException(status_code=401, detail="Not authenticated")

    app.dependency_overrides[get_current_user] = raise_401

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/patients/1/edit")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_patient_edit_returns_404_for_nonexistent():
    """GET /patients/{id}/edit 对不存在患者返回 404"""
    from fastapi import FastAPI
    from app.api.patient import router
    from app.api.auth import get_current_user

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/patients")

    mock_user = MagicMock()
    mock_user.account_id = 100
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with patch("app.api.patient.verify_patient_access", new_callable=AsyncMock) as mock_verify:
        from fastapi import HTTPException
        mock_verify.side_effect = HTTPException(status_code=404, detail="患者不存在")

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/patients/999/edit")

    assert response.status_code == 404