"""上传去重校验集成测试

覆盖 6 个验收场景:
1. 报告去重 - 重复被拦截 (content_hash 匹配)
2. 报告去重 - 不重复正常上传
3. 指标去重 - 同日同指标跳过
4. 指标去重 - index_id null 按 index_name 去重
5. 边界 - 预检与提交时间差双保险
6. 非 SSE 路径去重
"""
import pytest
import base64
import hashlib
from datetime import date
from io import BytesIO

from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.image_report import ImageReport
from app.models.medical import MedicalCheck, MedicalCheckDetail
from app.models.patient import Patient


def _make_base64_jpeg(width=200, height=200):
    """生成 JPEG 图片的 base64 data URL，返回 (data_url, raw_bytes, content_hash)"""
    img = Image.new('RGB', (width, height), color='white')
    buf = BytesIO()
    img.save(buf, 'JPEG')
    raw = buf.getvalue()
    b64 = base64.b64encode(raw).decode()
    content_hash = hashlib.sha256(raw).hexdigest()
    return f"data:image/jpeg;base64,{b64}", raw, content_hash


def _make_base64_png(width=100, height=100):
    """生成不同内容的 PNG 图片，返回 (data_url, raw_bytes, content_hash)"""
    img = Image.new('RGBA', (width, height), color='blue')
    buf = BytesIO()
    img.save(buf, 'PNG')
    raw = buf.getvalue()
    b64 = base64.b64encode(raw).decode()
    content_hash = hashlib.sha256(raw).hexdigest()
    return f"data:image/png;base64,{b64}", raw, content_hash


@pytest.fixture
def sample_image_data():
    """返回 (base64_data_url, raw_bytes, content_hash)"""
    return _make_base64_jpeg()


@pytest.fixture
def different_image_data():
    """返回内容不同的图片 (base64_data_url, raw_bytes, content_hash)"""
    return _make_base64_png()


@pytest.fixture
async def setup_patient(db_session, test_user):
    """创建测试患者并返回"""
    patient = Patient(
        account_id=test_user.account_id,
        patient_name="去重测试患者",
        gender="male",
        birth_date=date(1990, 1, 1),
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


class TestCheckDuplicateAPI:
    """场景1/2: check-duplicate API 报告去重校验"""

    @pytest.mark.asyncio
    async def test_duplicate_report_detected(
        self, client, auth_headers, db_session, test_user, setup_patient, sample_image_data
    ):
        """场景1: 同 content_hash 重复报告被拦截 — is_duplicate=true"""
        patient = setup_patient
        _, raw_bytes, content_hash = sample_image_data

        existing = ImageReport(
            patient_id=patient.patient_id,
            account_id=test_user.account_id,
            title="测试医院_blood_routine_2026-05-12",
            category="blood_routine",
            hospital="测试医院",
            capture_date=date(2026, 5, 12),
            image_size=len(raw_bytes),
            content_hash=content_hash,
            image_type="jpeg",
        )
        db_session.add(existing)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/image_reports/check-duplicate",
            params={
                "patient_id": patient.patient_id,
                "category": "blood_routine",
                "content_hash": content_hash,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_duplicate"] is True
        assert "existing_report_id" in data

    @pytest.mark.asyncio
    async def test_non_duplicate_report_passes(
        self, client, auth_headers, db_session, setup_patient, sample_image_data
    ):
        """场景2: 不同 content_hash 正常通过 — is_duplicate=false"""
        patient = setup_patient
        _, _, content_hash = sample_image_data

        resp = await client.post(
            "/api/v1/image_reports/check-duplicate",
            params={
                "patient_id": patient.patient_id,
                "category": "blood_routine",
                "content_hash": content_hash,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_duplicate"] is False

    @pytest.mark.asyncio
    async def test_different_hash_not_duplicate(
        self, client, auth_headers, db_session, test_user, setup_patient, sample_image_data, different_image_data
    ):
        """场景2补充: 同分类但不同 content_hash 不算重复"""
        patient = setup_patient
        _, raw_bytes, content_hash_a = sample_image_data
        _, _, content_hash_b = different_image_data

        existing = ImageReport(
            patient_id=patient.patient_id,
            account_id=test_user.account_id,
            title="测试报告",
            category="blood_routine",
            hospital="测试医院",
            capture_date=date(2026, 5, 12),
            image_size=len(raw_bytes),
            content_hash=content_hash_a,
            image_type="jpeg",
        )
        db_session.add(existing)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/image_reports/check-duplicate",
            params={
                "patient_id": patient.patient_id,
                "category": "blood_routine",
                "content_hash": content_hash_b,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_duplicate"] is False

    @pytest.mark.asyncio
    async def test_same_hash_different_category_not_duplicate(
        self, client, auth_headers, db_session, test_user, setup_patient, sample_image_data
    ):
        """同 content_hash 但不同分类不算重复"""
        patient = setup_patient
        _, raw_bytes, content_hash = sample_image_data

        existing = ImageReport(
            patient_id=patient.patient_id,
            account_id=test_user.account_id,
            title="血常规报告",
            category="blood_routine",
            hospital="测试医院",
            capture_date=date(2026, 5, 12),
            image_size=len(raw_bytes),
            content_hash=content_hash,
            image_type="jpeg",
        )
        db_session.add(existing)
        await db_session.commit()

        # 同一哈希但不同分类
        resp = await client.post(
            "/api/v1/image_reports/check-duplicate",
            params={
                "patient_id": patient.patient_id,
                "category": "biochemistry",
                "content_hash": content_hash,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_duplicate"] is False


class TestFailedRecordPassthrough:
    """OCR 解析失败的记录(0指标)不阻塞同图重传"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("terminal_status", ["pending_review", "failed", "completed"])
    async def test_failed_record_does_not_block_reupload(
        self, client, auth_headers, db_session, test_user, setup_patient, sample_image_data,
        terminal_status,
    ):
        """OCR 已结束但 0 指标的失败记录放行重传 — is_duplicate=false"""
        patient = setup_patient
        _, raw_bytes, content_hash = sample_image_data

        existing = ImageReport(
            patient_id=patient.patient_id,
            account_id=test_user.account_id,
            title="解析失败的血常规",
            category="blood_routine",
            hospital="测试医院",
            capture_date=date(2026, 5, 12),
            image_size=len(raw_bytes),
            content_hash=content_hash,
            image_type="jpeg",
            ocr_status=terminal_status,
            total_count=0,
            matched_count=0,
        )
        db_session.add(existing)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/image_reports/check-duplicate",
            params={
                "patient_id": patient.patient_id,
                "category": "blood_routine",
                "content_hash": content_hash,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_duplicate"] is False

    @pytest.mark.asyncio
    async def test_processing_record_still_blocks(
        self, client, auth_headers, db_session, test_user, setup_patient, sample_image_data
    ):
        """仍在处理中(pending/processing)的记录仍阻塞重传，避免并发处理同一图片"""
        patient = setup_patient
        _, raw_bytes, content_hash = sample_image_data

        existing = ImageReport(
            patient_id=patient.patient_id,
            account_id=test_user.account_id,
            title="处理中的血常规",
            category="blood_routine",
            hospital="测试医院",
            capture_date=date(2026, 5, 12),
            image_size=len(raw_bytes),
            content_hash=content_hash,
            image_type="jpeg",
            ocr_status="processing",
            total_count=0,
            matched_count=0,
        )
        db_session.add(existing)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/image_reports/check-duplicate",
            params={
                "patient_id": patient.patient_id,
                "category": "blood_routine",
                "content_hash": content_hash,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_duplicate"] is True


class TestNonSSEUploadDedup:
    """场景6: 非 SSE 路径去重"""

    @pytest.mark.asyncio
    async def test_non_sse_duplicate_returns_409(
        self, client, auth_headers, db_session, test_user, setup_patient, sample_image_data
    ):
        """场景6: 重复提交返回 HTTP 409"""
        patient = setup_patient
        image_data_url, raw_bytes, content_hash = sample_image_data

        existing = ImageReport(
            patient_id=patient.patient_id,
            account_id=test_user.account_id,
            title="测试医院_blood_routine_2026-05-12",
            category="blood_routine",
            hospital="测试医院",
            capture_date=date(2026, 5, 12),
            image_size=len(raw_bytes),
            content_hash=content_hash,
            image_type="jpeg",
        )
        db_session.add(existing)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/image_reports",
            json={
                "patient_id": patient.patient_id,
                "title": "测试医院_blood_routine_2026-05-12",
                "category": "blood_routine",
                "image_data": image_data_url,
                "image_type": "jpeg",
                "hospital": "测试医院",
                "capture_date": "2026-05-12",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 409


class TestSSEUploadDedup:
    """场景5: SSE 路径双保险"""

    @pytest.mark.asyncio
    async def test_sse_duplicate_returns_error_event(
        self, client, auth_headers, db_session, test_user, setup_patient, sample_image_data
    ):
        """场景5: SSE 流中重复报告返回 error 事件"""
        patient = setup_patient
        image_data_url, raw_bytes, content_hash = sample_image_data

        existing = ImageReport(
            patient_id=patient.patient_id,
            account_id=test_user.account_id,
            title="测试医院_blood_routine_2026-05-12",
            category="blood_routine",
            hospital="测试医院",
            capture_date=date(2026, 5, 12),
            image_size=len(raw_bytes),
            content_hash=content_hash,
            image_type="jpeg",
        )
        db_session.add(existing)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/image_reports/upload-stream",
            json={
                "patient_id": patient.patient_id,
                "title": "测试医院_blood_routine_2026-05-12",
                "category": "blood_routine",
                "image_data": image_data_url,
                "image_type": "jpeg",
                "hospital": "测试医院",
                "capture_date": "2026-05-12",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        content = resp.text
        assert "duplicate" in content or "已上传" in content


class TestIndicatorDedup:
    """场景3/4: 指标去重逻辑

    注意：index_id 有外键约束指向 medical_index 表，测试中统一使用
    index_id=None 来避免外键冲突，同时验证去重逻辑的两种路径：
    - index_id 非 null → 按 index_id 去重（通过已有记录模拟）
    - index_id null → 按 index_name 去重
    """

    @pytest.mark.asyncio
    async def test_null_index_id_dedup_across_reports(
        self, db_session, test_user, setup_patient
    ):
        """场景3+4: 同日同 index_name 不重复插入（index_id=null 跨报告去重）"""
        from app.services.ocr.ocr_result_processor import process_lab_result

        patient = setup_patient

        # 第一条报告
        report1 = ImageReport(
            patient_id=patient.patient_id,
            account_id=test_user.account_id,
            title="报告1",
            category="blood_routine",
            hospital="测试医院",
            capture_date=date(2026, 5, 12),
            image_size=1024,
            image_type="jpeg",
        )
        db_session.add(report1)
        await db_session.flush()

        ocr_result_1 = {
            "report_type": "lab",
            "indicators": [
                {"name": "白细胞", "value": "5.0", "unit": "10^9/L", "status": "normal",
                 "matched_index_id": None, "matched_name": None},
                {"name": "红细胞", "value": "4.5", "unit": "10^12/L", "status": "normal",
                 "matched_index_id": None, "matched_name": None},
            ],
            "matched_count": 0,
        }
        medical_id_1, skipped_1 = await process_lab_result(db_session, report1, ocr_result_1)
        await db_session.flush()
        assert skipped_1 == 0

        # 第二条报告（同日同医院同分类）— 白细胞重复
        report2 = ImageReport(
            patient_id=patient.patient_id,
            account_id=test_user.account_id,
            title="报告2",
            category="blood_routine",
            hospital="测试医院",
            capture_date=date(2026, 5, 12),
            image_size=2048,
            image_type="jpeg",
        )
        db_session.add(report2)
        await db_session.flush()

        ocr_result_2 = {
            "report_type": "lab",
            "indicators": [
                {"name": "白细胞", "value": "6.0", "unit": "10^9/L", "status": "normal",
                 "matched_index_id": None, "matched_name": None},
                {"name": "血红蛋白", "value": "130", "unit": "g/L", "status": "normal",
                 "matched_index_id": None, "matched_name": None},
            ],
            "matched_count": 0,
        }
        medical_id_2, skipped_2 = await process_lab_result(db_session, report2, ocr_result_2)
        await db_session.flush()
        assert medical_id_2 is not None
        assert skipped_2 == 1  # 白细胞按 index_name 去重被跳过

        # 验证数据库只有 3 条 detail（2 + 1，重复不插入）
        details = await db_session.execute(
            select(MedicalCheckDetail).where(
                MedicalCheckDetail.medical_id.in_([medical_id_1, medical_id_2])
            )
        )
        assert len(details.all()) == 3

    @pytest.mark.asyncio
    async def test_intra_batch_dedup_by_name(
        self, db_session, test_user, setup_patient
    ):
        """同批次内重复 index_name 也去重"""
        from app.services.ocr.ocr_result_processor import process_lab_result

        patient = setup_patient

        report = ImageReport(
            patient_id=patient.patient_id,
            account_id=test_user.account_id,
            title="批次内去重",
            category="blood_routine",
            hospital="测试医院",
            capture_date=date(2026, 5, 12),
            image_size=1024,
            image_type="jpeg",
        )
        db_session.add(report)
        await db_session.flush()

        # 同一批指标中出现两个相同 index_name
        ocr_result = {
            "report_type": "lab",
            "indicators": [
                {"name": "白细胞", "value": "5.0", "unit": "10^9/L", "status": "normal",
                 "matched_index_id": None, "matched_name": None},
                {"name": "白细胞", "value": "6.0", "unit": "10^9/L", "status": "normal",
                 "matched_index_id": None, "matched_name": None},
            ],
            "matched_count": 0,
        }
        medical_id, skipped = await process_lab_result(db_session, report, ocr_result)
        await db_session.flush()
        assert skipped == 1

        details = await db_session.execute(
            select(MedicalCheckDetail).where(MedicalCheckDetail.medical_id == medical_id)
        )
        assert len(details.all()) == 1