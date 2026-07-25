"""测试每日状态记录功能"""
import pytest
from httpx import AsyncClient

from app.models.patient import Patient
from app.models.user import LoginAccount
from app.core.security import get_password_hash


@pytest.fixture
async def status_user(db_session):
    """创建测试用户"""
    import uuid
    unique_username = f"status_user_{uuid.uuid4().hex[:8]}"
    
    user = LoginAccount(
        username=unique_username,
        password=get_password_hash("test123456"),
        account_name="状态测试用户",
        status="active"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def status_patient(db_session, status_user: LoginAccount):
    """创建测试患者"""
    patient = Patient(
        account_id=status_user.account_id,
        patient_name="测试患者",
        gender="male"
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest.fixture
async def status_auth_headers(client, status_user: LoginAccount):
    """获取认证头"""
    response = await client.post("/api/v1/auth/login", json={
        "username": status_user.username,
        "password": "test123456"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_daily_status(
    client: AsyncClient,
    status_user: LoginAccount,
    status_patient: Patient,
    status_auth_headers: dict
):
    """测试创建每日状态记录"""
    # 创建状态记录
    data = {
        "patient_id": status_patient.patient_id,
        "event_type": "life",
        "category": "daily_status",
        "title": "03月20日 · 心情8 / 睡眠6",
        "event_date": "2024-03-20",
        "description": "整体感觉不错",
        "life_details": {
            "mood": {"score": 8, "max_score": 10},
            "pain": {"score": 0, "max_score": 10},
            "sleep": {"score": 6, "max_score": 10},
            "diet": {"score": 7, "max_score": 10},
            "stool": {"status": "normal", "memo": ""},
            "general_memo": "整体感觉不错",
            "memo_items": []
        }
    }

    response = await client.post(
        "/api/v1/timeline/events",
        json=data,
        headers=status_auth_headers
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result["category"] == "daily_status"
    assert result["life_details"]["mood"]["score"] == 8
    assert result["life_details"]["pain"]["score"] == 0
    assert result["life_details"]["sleep"]["score"] == 6
    assert result["life_details"]["diet"]["score"] == 7


@pytest.mark.asyncio
async def test_query_daily_status(
    client: AsyncClient,
    status_user: LoginAccount,
    status_patient: Patient,
    status_auth_headers: dict
):
    """测试查询每日状态记录"""
    # 创建状态记录
    create_data = {
        "patient_id": status_patient.patient_id,
        "event_type": "life",
        "category": "daily_status",
        "title": "03月21日状态记录",
        "event_date": "2024-03-21",
        "life_details": {
            "mood": {"score": 9, "max_score": 10},
            "pain": {"score": 1, "max_score": 10},
            "general_memo": "今天很好"
        }
    }
    await client.post(
        "/api/v1/timeline/events",
        json=create_data,
        headers=status_auth_headers
    )

    # 查询状态记录
    query_data = {
        "patient_id": status_patient.patient_id,
        "event_type": "life",
        "category": "daily_status"
    }
    response = await client.post(
        "/api/v1/timeline/events/query",
        json=query_data,
        headers=status_auth_headers
    )
    
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    # 验证返回的记录包含所有状态类型
    found = False
    for item in results:
        if item["category"] == "daily_status":
            found = True
            assert "mood" in item["life_details"]
            assert item["life_details"]["mood"]["score"] == 9
            break
    assert found, "应该找到 daily_status 类型的记录"


@pytest.mark.asyncio
async def test_update_daily_status(
    client: AsyncClient,
    status_user: LoginAccount,
    status_patient: Patient,
    status_auth_headers: dict
):
    """测试更新每日状态记录"""
    # 创建状态记录
    create_data = {
        "patient_id": status_patient.patient_id,
        "event_type": "life",
        "category": "daily_status",
        "title": "03月22日状态记录",
        "event_date": "2024-03-22",
        "life_details": {
            "mood": {"score": 5, "max_score": 10}
        }
    }
    create_resp = await client.post(
        "/api/v1/timeline/events",
        json=create_data,
        headers=status_auth_headers
    )
    event_id = create_resp.json()["event_id"]

    # 更新状态记录
    update_data = {
        "life_details": {
            "mood": {"score": 8, "max_score": 10},
            "pain": {"score": 2, "max_score": 10},
            "sleep": {"score": 7, "max_score": 10},
            "general_memo": "更新后的备注"
        }
    }
    response = await client.put(
        f"/api/v1/timeline/events/{event_id}",
        json=update_data,
        headers=status_auth_headers
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result["life_details"]["mood"]["score"] == 8
    assert result["life_details"]["pain"]["score"] == 2
    assert result["life_details"]["sleep"]["score"] == 7
    assert result["life_details"]["general_memo"] == "更新后的备注"


@pytest.mark.asyncio
async def test_stool_status_options(
    client: AsyncClient,
    status_user: LoginAccount,
    status_patient: Patient,
    status_auth_headers: dict
):
    """测试大便状态的不同选项"""
    # 创建包含不同大便状态的记录
    stool_statuses = ["normal", "loose", "constipation"]
    
    for i, status in enumerate(stool_statuses):
        data = {
            "patient_id": status_patient.patient_id,
            "event_type": "life",
            "category": "daily_status",
            "title": f"03月{23+i}日状态记录",
            "event_date": f"2024-03-2{3+i}",
            "life_details": {
                "stool": {"status": status, "memo": f"测试{i}"}
            }
        }
        response = await client.post(
            "/api/v1/timeline/events",
            json=data,
            headers=status_auth_headers
        )
        assert response.status_code == 200
        result = response.json()
        assert result["life_details"]["stool"]["status"] == status