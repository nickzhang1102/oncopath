"""时间线 API 测试"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.timeline import TimelineEvent


class TestTimelineAPI:
    """时间线 API 测试"""

    @pytest.mark.asyncio
    async def test_query_timeline_events(
        self, client, test_user, auth_headers, db_session
    ):
        """测试查询时间线事件"""
        # 创建测试患者
        patient = Patient(
            account_id=test_user.account_id,
            patient_name="时间线患者",
            gender="male",
            birth_date=date(1990, 1, 1)
        )
        db_session.add(patient)
        await db_session.commit()
        await db_session.refresh(patient)

        # 创建测试事件
        event1 = TimelineEvent(
            patient_id=patient.patient_id,
            event_type="medical",
            category="chemotherapy",
            event_date=date(2024, 1, 15),
            title="第1周期化疗",
            description="开始化疗",
            medical_details={"hospital": "中山医院", "memo_items": []}
        )
        event2 = TimelineEvent(
            patient_id=patient.patient_id,
            event_type="life",
            category="mood",
            event_date=date(2024, 1, 20),
            title="心情不错",
            description="感觉良好",
            life_details={"score": 8, "max_score": 10, "memo_items": []}
        )
        db_session.add_all([event1, event2])
        await db_session.commit()

        # 查询时间线
        response = await client.post(
            "/api/v1/timeline/events/query",
            json={
                "patient_id": patient.patient_id
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_create_medical_event(
        self, client, test_user, auth_headers, db_session
    ):
        """测试创建医疗事件（治疗记录）"""
        # 创建测试患者
        patient = Patient(
            account_id=test_user.account_id,
            patient_name="治疗患者",
            gender="male",
            birth_date=date(1990, 1, 1)
        )
        db_session.add(patient)
        await db_session.commit()
        await db_session.refresh(patient)

        # 创建治疗记录
        response = await client.post(
            "/api/v1/timeline/events",
            json={
                "patient_id": patient.patient_id,
                "event_type": "medical",
                "category": "chemotherapy",
                "event_date": "2024-03-15",
                "title": "第3周期化疗",
                "description": "顺利完成化疗",
                "medical_details": {
                    "hospital": "中山医院",
                    "doctor": "张医生",
                    "cycle": "第3周期",
                    "memo_items": [
                        {"time": "09:00", "event": "入院办理"},
                        {"time": "14:00", "event": "开始化疗用药"}
                    ]
                }
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "第3周期化疗"
        assert data["category"] == "chemotherapy"
        assert data["medical_details"]["hospital"] == "中山医院"

    @pytest.mark.asyncio
    async def test_create_life_event(
        self, client, test_user, auth_headers, db_session
    ):
        """测试创建生活事件（状态记录）"""
        # 创建测试患者
        patient = Patient(
            account_id=test_user.account_id,
            patient_name="状态患者",
            gender="female",
            birth_date=date(1985, 5, 20)
        )
        db_session.add(patient)
        await db_session.commit()
        await db_session.refresh(patient)

        # 创建状态记录
        response = await client.post(
            "/api/v1/timeline/events",
            json={
                "patient_id": patient.patient_id,
                "event_type": "life",
                "category": "mood",
                "event_date": "2024-03-20",
                "title": "今天心情不错",
                "description": "食欲恢复，精神状态良好",
                "life_details": {
                    "score": 8,
                    "max_score": 10,
                    "memo_items": [
                        {"time": "08:00", "event": "起床，感觉精神不错"},
                        {"time": "12:00", "event": "午餐食欲良好"}
                    ]
                }
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "今天心情不错"
        assert data["category"] == "mood"
        assert data["life_details"]["score"] == 8

    @pytest.mark.asyncio
    async def test_query_by_event_type(
        self, client, test_user, auth_headers, db_session
    ):
        """测试按事件类型筛选"""
        # 创建测试患者
        patient = Patient(
            account_id=test_user.account_id,
            patient_name="筛选患者",
            gender="male",
            birth_date=date(1990, 1, 1)
        )
        db_session.add(patient)
        await db_session.commit()
        await db_session.refresh(patient)

        # 创建不同类型事件
        for i in range(3):
            medical_event = TimelineEvent(
                patient_id=patient.patient_id,
                event_type="medical",
                category="chemotherapy",
                event_date=date(2024, 1, i+1),
                title=f"医疗事件{i}"
            )
            life_event = TimelineEvent(
                patient_id=patient.patient_id,
                event_type="life",
                category="mood",
                event_date=date(2024, 2, i+1),
                title=f"生活事件{i}"
            )
            db_session.add_all([medical_event, life_event])
        await db_session.commit()

        # 查询医疗事件
        response = await client.post(
            "/api/v1/timeline/events/query",
            json={
                "patient_id": patient.patient_id,
                "event_type": "medical"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(e["event_type"] == "medical" for e in data)

    @pytest.mark.asyncio
    async def test_query_by_category(
        self, client, test_user, auth_headers, db_session
    ):
        """测试按分类筛选"""
        # 创建测试患者
        patient = Patient(
            account_id=test_user.account_id,
            patient_name="分类患者",
            gender="male",
            birth_date=date(1990, 1, 1)
        )
        db_session.add(patient)
        await db_session.commit()
        await db_session.refresh(patient)

        # 创建不同分类事件
        categories = ["chemotherapy", "radiation", "surgery", "mood", "pain"]
        for i, cat in enumerate(categories):
            event = TimelineEvent(
                patient_id=patient.patient_id,
                event_type="medical" if i < 3 else "life",
                category=cat,
                event_date=date(2024, 1, i+1),
                title=f"{cat}事件"
            )
            db_session.add(event)
        await db_session.commit()

        # 查询化疗事件
        response = await client.post(
            "/api/v1/timeline/events/query",
            json={
                "patient_id": patient.patient_id,
                "category": "chemotherapy"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["category"] == "chemotherapy"

    @pytest.mark.asyncio
    async def test_update_timeline_event(
        self, client, test_user, auth_headers, db_session
    ):
        """测试更新时间线事件"""
        # 创建测试患者
        patient = Patient(
            account_id=test_user.account_id,
            patient_name="更新患者",
            gender="male",
            birth_date=date(1990, 1, 1)
        )
        db_session.add(patient)
        await db_session.commit()
        await db_session.refresh(patient)

        # 创建事件
        event = TimelineEvent(
            patient_id=patient.patient_id,
            event_type="medical",
            category="chemotherapy",
            event_date=date(2024, 1, 15),
            title="原标题"
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        # 更新事件
        response = await client.put(
            f"/api/v1/timeline/events/{event.event_id}",
            json={
                "title": "更新后的标题",
                "description": "添加描述",
                "medical_details": {
                    "hospital": "新医院",
                    "memo_items": []
                }
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "更新后的标题"
        assert data["description"] == "添加描述"

    @pytest.mark.asyncio
    async def test_delete_timeline_event(
        self, client, test_user, auth_headers, db_session
    ):
        """测试删除时间线事件"""
        # 创建测试患者
        patient = Patient(
            account_id=test_user.account_id,
            patient_name="删除患者",
            gender="male",
            birth_date=date(1990, 1, 1)
        )
        db_session.add(patient)
        await db_session.commit()
        await db_session.refresh(patient)

        # 创建事件
        event = TimelineEvent(
            patient_id=patient.patient_id,
            event_type="medical",
            category="chemotherapy",
            event_date=date(2024, 1, 15),
            title="待删除事件"
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        event_id = event.event_id

        # 删除事件
        response = await client.delete(
            f"/api/v1/timeline/events/{event_id}",
            headers=auth_headers
        )
        assert response.status_code == 200

        # 验证已删除
        from sqlalchemy import text
        result = await db_session.execute(
            text("SELECT * FROM timeline_events WHERE event_id = :eid"),
            {"eid": event_id}
        )
        assert result.first() is None

    @pytest.mark.asyncio
    async def test_get_timeline_stats(
        self, client, test_user, auth_headers, db_session
    ):
        """测试获取时间线统计"""
        # 创建测试患者
        patient = Patient(
            account_id=test_user.account_id,
            patient_name="统计患者",
            gender="male",
            birth_date=date(1990, 1, 1)
        )
        db_session.add(patient)
        await db_session.commit()
        await db_session.refresh(patient)

        # 创建多个事件
        for i in range(5):
            event = TimelineEvent(
                patient_id=patient.patient_id,
                event_type="medical" if i < 3 else "life",
                category=["chemotherapy", "surgery", "mood"][i % 3],
                event_date=date(2024, 1, i+1),
                title=f"事件{i}"
            )
            db_session.add(event)
        await db_session.commit()

        # 获取统计
        response = await client.get(
            f"/api/v1/timeline/stats/{patient.patient_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 5
        assert data["medical_events"] == 3
        assert data["life_events"] == 2

    @pytest.mark.asyncio
    async def test_query_with_date_range(
        self, client, test_user, auth_headers, db_session
    ):
        """测试日期范围查询"""
        # 创建测试患者
        patient = Patient(
            account_id=test_user.account_id,
            patient_name="日期范围患者",
            gender="male",
            birth_date=date(1990, 1, 1)
        )
        db_session.add(patient)
        await db_session.commit()
        await db_session.refresh(patient)

        # 创建不同日期的事件
        for month in [1, 2, 3, 4]:
            event = TimelineEvent(
                patient_id=patient.patient_id,
                event_type="medical",
                category="chemotherapy",
                event_date=date(2024, month, 15),
                title=f"{month}月事件"
            )
            db_session.add(event)
        await db_session.commit()

        # 查询2月到3月
        response = await client.post(
            "/api/v1/timeline/events/query",
            json={
                "patient_id": patient.patient_id,
                "start_date": "2024-02-01",
                "end_date": "2024-03-31"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2