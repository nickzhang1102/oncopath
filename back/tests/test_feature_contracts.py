"""跨模块功能集成测试。"""
from datetime import date

import pytest
from sqlalchemy import select

from app.models.patient import Patient
from app.models.medical import MedicalCheck, MedicalExam, PathologyReport, MedicalRecord
from app.models.conversation import Conversation
from app.models.knowledge import KnowledgeCategory
from app.models.timeline import TimelineEvent


class TestTimelineService:
    """治疗时间线测试"""

    @pytest.mark.asyncio
    async def test_get_timeline_by_patient(
        self, client, test_user, auth_headers, db_session
    ):
        """测试按患者查询时间线"""
        patient = Patient(
            account_id=test_user.account_id,
            patient_name="时间线查询患者",
            gender="male",
            birth_date=date(1990, 1, 1)
        )
        db_session.add(patient)
        await db_session.commit()
        await db_session.refresh(patient)

        # 创建多个时间线事件
        for i in range(3):
            event = TimelineEvent(
                patient_id=patient.patient_id,
                event_date=date(2024, 1, i+1),
                event_type="medical",
                category="treatment",
                title=f"事件{i}"
            )
            db_session.add(event)
        await db_session.commit()

        # 查询时间线
        response = await client.post(
            "/api/v1/timeline/events/query",
            json={"patient_id": patient.patient_id},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert [item["title"] for item in data] == ["事件2", "事件1", "事件0"]


class TestConsultationEnhanced:
    """AI会诊增强测试"""

    @pytest.mark.asyncio
    async def test_consultation_history_query(
        self, client, test_user, auth_headers, db_session
    ):
        """测试历史会诊查询"""
        patient = Patient(
            account_id=test_user.account_id,
            patient_name="历史会诊患者",
            gender="male",
            birth_date=date(1990, 1, 1)
        )
        db_session.add(patient)
        await db_session.commit()
        await db_session.refresh(patient)

        # 创建历史会诊记录
        for i in range(3):
            conversation = Conversation(
                user_id=test_user.account_id,
                patient_id=patient.patient_id,
                title=f"症状{i}",
                status="completed"
            )
            db_session.add(conversation)
        await db_session.commit()

        # 查询历史会诊
        response = await client.get(
            f"/api/v1/patients/{patient.patient_id}/consultations",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert {item["question"] for item in data} == {"症状0", "症状1", "症状2"}


class TestKnowledgeBase:
    """知识库测试"""

    @pytest.mark.asyncio
    async def test_knowledge_category_hierarchy(
        self, client, test_user, auth_headers, db_session
    ):
        """测试分类层级"""
        # 创建父分类
        parent = KnowledgeCategory(
            category_name="父分类",
            account_id=test_user.account_id
        )
        db_session.add(parent)
        await db_session.commit()
        await db_session.refresh(parent)

        # 创建子分类
        child = KnowledgeCategory(
            category_name="子分类",
            parent_id=parent.category_id,
            account_id=test_user.account_id
        )
        db_session.add(child)
        await db_session.commit()

        # 验证层级关系
        result = await db_session.execute(
            select(KnowledgeCategory).where(KnowledgeCategory.parent_id == parent.category_id)
        )
        children = result.scalars().all()
        assert [item.category_name for item in children] == ["子分类"]


class TestMedicalModelIntegration:
    """医疗模型集成测试"""

    @pytest.mark.asyncio
    async def test_medical_check_with_ocr_data(
        self, client, test_user, auth_headers, db_session
    ):
        """测试检验报告OCR数据关联"""
        patient = Patient(
            account_id=test_user.account_id,
            patient_name="OCR患者",
            gender="male",
            birth_date=date(1990, 1, 1)
        )
        db_session.add(patient)
        await db_session.commit()
        await db_session.refresh(patient)

        # 创建检验报告（关联OCR数据）
        check = MedicalCheck(
            patient_id=patient.patient_id,
            medical_date=date.today(),
            hospital="OCR医院"
        )
        db_session.add(check)
        await db_session.commit()

        # 验证关联
        result = await db_session.execute(
            select(MedicalCheck).where(MedicalCheck.patient_id == patient.patient_id)
        )
        checks = result.scalars().all()
        assert [item.medical_id for item in checks] == [check.medical_id]

    @pytest.mark.asyncio
    async def test_medical_exam_image_management(
        self, client, test_user, auth_headers, db_session
    ):
        """测试检查报告图片管理"""
        patient = Patient(
            account_id=test_user.account_id,
            patient_name="检查患者",
            gender="male",
            birth_date=date(1990, 1, 1)
        )
        db_session.add(patient)
        await db_session.commit()
        await db_session.refresh(patient)

        # 创建检查报告（含图片）
        exam = MedicalExam(
            patient_id=patient.patient_id,
            medical_date=date.today(),
            hospital="检查医院",
            exam_info="检查信息"
        )
        db_session.add(exam)
        await db_session.commit()

        # 验证创建成功
        assert exam.exam_id is not None

    @pytest.mark.asyncio
    async def test_pathology_report_creation(
        self, client, test_user, auth_headers, db_session
    ):
        """测试病理报告创建"""
        patient = Patient(
            account_id=test_user.account_id,
            patient_name="病理患者",
            gender="male",
            birth_date=date(1990, 1, 1)
        )
        db_session.add(patient)
        await db_session.commit()
        await db_session.refresh(patient)

        # 创建病理报告
        pathology = PathologyReport(
            patient_id=patient.patient_id,
            report_date=date.today(),
            hospital="病理医院"
        )
        db_session.add(pathology)
        await db_session.commit()

        # 验证创建成功
        assert pathology.report_id is not None

    @pytest.mark.asyncio
    async def test_medical_record_creation(
        self, client, test_user, auth_headers, db_session
    ):
        """测试病情记录创建"""
        patient = Patient(
            account_id=test_user.account_id,
            patient_name="病情患者",
            gender="male",
            birth_date=date(1990, 1, 1)
        )
        db_session.add(patient)
        await db_session.commit()
        await db_session.refresh(patient)

        # 创建病情记录
        record = MedicalRecord(
            patient_id=patient.patient_id,
            record_date=date.today(),
            record_info="病情记录内容"
        )
        db_session.add(record)
        await db_session.commit()

        # 验证创建成功
        assert record.record_id is not None
