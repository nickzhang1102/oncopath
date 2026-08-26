from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional
from datetime import date
from contextlib import asynccontextmanager

from app.core.database import get_db, async_session_factory
from app.api.auth import get_current_user
from app.api.deps import verify_patient_access
from app.utils.time_utils import calculate_age
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.medical import MedicalCheck, MedicalCheckDetail, MedicalExam, PathologyReport
from app.models.medication import Medication
from app.models.image_report import ImageReport
from app.models.conversation import LeaderSession
from app.schemas.dashboard import (
    DashboardResponse, DashboardAbnormalIndicator, DashboardActiveMedication,
    DashboardTimelineEvent,
)
from app.services.timeline_aggregator import fetch_unified_timeline, fetch_unified_stats
from app.services.desensitization import desensitization_service
from app.services.encryption_service import encryption_service

router = APIRouter()


@asynccontextmanager
async def _independent_session():
    """创建独立的数据库会话，用于并行查询避免同一 session 并发冲突"""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def _query_counts(patient_id: int) -> dict:
    """一次性查询所有计数指标（单连接串行，COUNT 查询极快）"""
    async with _independent_session() as db:
        from app.models.timeline import TimelineEvent

        check_count = (await db.execute(
            select(func.count(MedicalCheck.medical_id)).where(MedicalCheck.patient_id == patient_id)
        )).scalar() or 0

        exam_count = (await db.execute(
            select(func.count(MedicalExam.exam_id)).where(MedicalExam.patient_id == patient_id)
        )).scalar() or 0

        pathology_count = (await db.execute(
            select(func.count(PathologyReport.report_id)).where(PathologyReport.patient_id == patient_id)
        )).scalar() or 0

        timeline_count = (await db.execute(
            select(func.count(TimelineEvent.event_id)).where(TimelineEvent.patient_id == patient_id)
        )).scalar() or 0

        med_total = (await db.execute(
            select(func.count(Medication.id)).where(Medication.patient_id == patient_id)
        )).scalar() or 0

        pending_review_count = (await db.execute(
            select(func.count(ImageReport.report_id)).where(
                ImageReport.patient_id == patient_id,
                ImageReport.ocr_status == "pending_review",
            )
        )).scalar() or 0

        ongoing_consult_count = (await db.execute(
            select(func.count(LeaderSession.id)).where(
                LeaderSession.patient_id == patient_id,
                LeaderSession.state.in_(["assessing", "questioning", "forming_team", "monitoring", "summarizing"]),
            )
        )).scalar() or 0

        return {
            "check_count": check_count,
            "exam_count": exam_count,
            "pathology_count": pathology_count,
            "timeline_count": timeline_count,
            "med_total": med_total,
            "pending_review_count": pending_review_count,
            "ongoing_consult_count": ongoing_consult_count,
        }


async def _query_active_meds(patient_id: int):
    """查询当前用药"""
    async with _independent_session() as db:
        result = await db.execute(
            select(Medication)
            .where(Medication.patient_id == patient_id, Medication.status == "active")
            .order_by(desc(Medication.start_date))
            .limit(5)
        )
        return result.scalars().all()


async def _query_abnormal_indicators(patient_id: int):
    """查询异常指标"""
    async with _independent_session() as db:
        result = await db.execute(
            select(MedicalCheckDetail, MedicalCheck.medical_date)
            .join(MedicalCheck, MedicalCheckDetail.medical_id == MedicalCheck.medical_id)
            .where(
                MedicalCheck.patient_id == patient_id,
                MedicalCheckDetail.index_status.in_(["high", "low", "abnormal"]),
            )
            .order_by(desc(MedicalCheck.medical_date))
            .limit(5)
        )
        return result.all()


async def _query_recent_events(patient_id: int) -> list:
    """获取近期3条统一时间线事件"""
    async with _independent_session() as db:
        from app.schemas.timeline import UnifiedTimelineQuery
        query = UnifiedTimelineQuery(patient_id=patient_id, limit=3)
        items = await fetch_unified_timeline(db, query)
        return [
            DashboardTimelineEvent(
                id=item.id,
                source_type=item.source_type,
                title=item.title,
                event_date=item.event_date,
                category=item.category,
            )
            for item in items[:3]
        ]


async def _query_timeline_stats(patient_id: int):
    """查询时间线统计"""
    async with _independent_session() as db:
        return await fetch_unified_stats(db, patient_id)


@router.get("/{patient_id}", response_model=DashboardResponse)
async def get_dashboard(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """获取首页仪表盘聚合数据"""
    # 权限验证使用原始 db session
    patient = await verify_patient_access(db, patient_id, current_user.account_id)

    # 解密患者姓名
    patient_name = None
    if patient.patient_name:
        try:
            patient_name = encryption_service.decrypt(patient.patient_name)
            patient_name = desensitization_service.mask_name(patient_name)
        except Exception:
            patient_name = "***"

    # 并行查询：COUNT 合并为1个连接 + 列表查询各1个连接（共6个连接，远低于原13个）
    from asyncio import gather, wait_for, TimeoutError as AsyncTimeoutError

    try:
        (
            counts,
            active_meds_list,
            abnormal_rows,
            recent_events,
            stats,
        ) = await wait_for(gather(
            _query_counts(patient_id),
            _query_active_meds(patient_id),
            _query_abnormal_indicators(patient_id),
            _query_recent_events(patient_id),
            _query_timeline_stats(patient_id),
        ), timeout=10.0)
    except AsyncTimeoutError:
        raise HTTPException(status_code=504, detail="仪表盘数据加载超时，请稍后重试")

    # 组装异常指标
    abnormal_indicators = []
    for detail, medical_date in abnormal_rows:
        abnormal_indicators.append(DashboardAbnormalIndicator(
            index_name=detail.index_name,
            index_value=detail.index_value,
            index_unit=detail.index_unit,
            index_status=detail.index_status,
            medical_date=medical_date,
        ))

    # 组装当前用药
    active_medications = [
        DashboardActiveMedication(
            medication_name=m.medication_name,
            dosage=m.dosage,
            frequency=m.frequency,
            route=m.route,
            status=m.status,
        )
        for m in active_meds_list
    ]

    # 日期范围
    date_range = stats.date_range if stats else {}

    # 解密脱敏后的手机号和身份证
    patient_phone = None
    if patient.patient_phone:
        try:
            patient_phone = desensitization_service.mask_phone(
                encryption_service.decrypt(patient.patient_phone)
            )
        except Exception:
            patient_phone = "***"

    id_card = None
    if patient.id_card:
        try:
            id_card = desensitization_service.mask_id_card(
                encryption_service.decrypt(patient.id_card)
            )
        except Exception:
            id_card = "***"

    # 解密紧急联系人
    emergency_contact = None
    if patient.emergency_contact:
        try:
            emergency_contact = desensitization_service.mask_name(
                encryption_service.decrypt(patient.emergency_contact)
            )
        except Exception:
            emergency_contact = "***"

    emergency_phone = None
    if patient.emergency_phone:
        try:
            emergency_phone = desensitization_service.mask_phone(
                encryption_service.decrypt(patient.emergency_phone)
            )
        except Exception:
            emergency_phone = "***"

    return DashboardResponse(
        patient_name=patient_name,
        age=calculate_age(patient.birth_date) if patient.birth_date else None,
        gender=patient.gender,
        medical_history=patient.medical_history,
        id_card=id_card,
        patient_phone=patient_phone,
        emergency_contact=emergency_contact,
        emergency_phone=emergency_phone,
        allergies=patient.allergies,
        active_medications=active_medications,
        abnormal_indicator_count=len(abnormal_rows),
        abnormal_indicators=abnormal_indicators,
        recent_events=recent_events,
        check_count=counts["check_count"],
        exam_count=counts["exam_count"],
        pathology_count=counts["pathology_count"],
        timeline_event_count=counts["timeline_count"],
        medication_total=counts["med_total"],
        pending_review_count=counts["pending_review_count"],
        ongoing_consultation_count=counts["ongoing_consult_count"],
        earliest_date=date_range.get("start"),
        latest_date=date_range.get("end"),
    )
