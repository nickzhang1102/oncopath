"""
测试首页API接口

运行方式:
pytest test_homepage_api.py -v
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.main import app
from app.core.database import get_db
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.medical import MedicalType, MedicalIndex, MedicalCheck, MedicalCheckDetail
from app.core.security import get_password_hash, create_access_token


@pytest.fixture
async def test_data(db: AsyncSession):
    """创建测试数据"""
    # 创建测试用户
    user = LoginAccount(
        username="test_user",
        password_hash=get_password_hash("test123"),
        email="test@example.com"
    )
    db.add(user)
    await db.flush()

    # 创建测试患者
    patient = Patient(
        patient_name="测试患者",
        account_id=user.account_id,
        gender="男",
        birth_date=date(1990, 1, 1)
    )
    db.add(patient)
    await db.flush()

    # 创建医疗类型
    blood_type = MedicalType(type_name="血常规", sort=1)
    tumor_type = MedicalType(type_name="肿瘤标志物", sort=2)
    db.add_all([blood_type, tumor_type])
    await db.flush()

    # 创建标准指标
    wbc_index = MedicalIndex(
        index_name="白细胞计数",
        index_code="WBC",
        index_unit="10^9/L",
        reference_min=4.0,
        reference_max=10.0,
        medical_type=blood_type.type_id,
        category="血常规",
        is_active=True
    )
    db.add(wbc_index)
    await db.flush()

    # 创建检验记录
    check = MedicalCheck(
        patient_id=patient.patient_id,
        medical_date=date(2026, 3, 15),
        hospital="测试医院",
        medical_type=blood_type.type_id
    )
    db.add(check)
    await db.flush()

    # 创建检验明细
    detail = MedicalCheckDetail(
        medical_id=check.medical_id,
        index_id=wbc_index.index_id,
        index_name="白细胞计数",
        index_value="8.5",
        index_unit="10^9/L",
        reference_value="4.0-10.0",
        index_status="normal"
    )
    db.add(detail)
    await db.commit()

    # 生成访问令牌
    token = create_access_token(data={"sub": user.username})

    return {
        "user": user,
        "patient": patient,
        "blood_type": blood_type,
        "tumor_type": tumor_type,
        "wbc_index": wbc_index,
        "check": check,
        "detail": detail,
        "token": token
    }


@pytest.mark.asyncio
async def test_get_latest_check_data(db: AsyncSession, test_data):
    """测试获取最新检验数据接口"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 设置数据库会话
        app.dependency_overrides[get_db] = lambda: db

        response = await client.get(
            "/api/v1/medical/checks/latest",
            params={
                "patient_id": test_data["patient"].patient_id,
                "medical_type": test_data["blood_type"].type_id,
                "limit": 10
            },
            headers={"Authorization": f"Bearer {test_data['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["medical_id"] == test_data["check"].medical_id
        assert len(data[0]["indices"]) > 0


@pytest.mark.asyncio
async def test_get_indices(db: AsyncSession, test_data):
    """测试获取指标列表接口"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        app.dependency_overrides[get_db] = lambda: db

        response = await client.get(
            "/api/v1/medical/indices",
            params={
                "patient_id": test_data["patient"].patient_id,
                "medical_type": test_data["blood_type"].type_id
            },
            headers={"Authorization": f"Bearer {test_data['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["index_code"] == "WBC"


@pytest.mark.asyncio
async def test_get_index_history(db: AsyncSession, test_data):
    """测试获取指标历史接口"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        app.dependency_overrides[get_db] = lambda: db

        response = await client.get(
            "/api/v1/medical/indices/history",
            params={
                "index_name": "白细胞计数",
                "patient_id": test_data["patient"].patient_id
            },
            headers={"Authorization": f"Bearer {test_data['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["index_name"] == "白细胞计数"
        assert data[0]["index_value"] == "8.5"


@pytest.mark.asyncio
async def test_get_latest_exam_report(db: AsyncSession, test_data):
    """测试获取最新检查报告接口"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        app.dependency_overrides[get_db] = lambda: db

        response = await client.get(
            "/api/v1/medical/exams/latest",
            params={
                "patient_id": test_data["patient"].patient_id,
                "limit": 10
            },
            headers={"Authorization": f"Bearer {test_data['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
