"""全局搜索 API - 跨模块搜索"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
from pydantic import BaseModel
from typing import Optional, List

from app.core.database import get_db
from app.api.auth import get_current_user
from app.api.deps import verify_patient_access
from app.models.user import LoginAccount
from app.models.medical import MedicalCheck, MedicalCheckDetail, MedicalExam, PathologyReport
from app.models.medication import Medication
from app.models.timeline import TimelineEvent

router = APIRouter(prefix="/search", tags=["全局搜索"])


class SearchResultItem(BaseModel):
    module: str  # check/exam/pathology/medication/timeline
    id: int
    title: str
    subtitle: str
    date: Optional[str] = None


class SearchResponse(BaseModel):
    keyword: str
    total: int
    items: List[SearchResultItem]


@router.get("", response_model=SearchResponse)
async def global_search(
    patient_id: int = Query(..., description="患者ID"),
    keyword: str = Query(..., min_length=1, max_length=100, description="搜索关键词"),
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """全局搜索：跨模块搜索检验指标、检查报告、病理、用药、时间线"""
    await verify_patient_access(db, patient_id, current_user.account_id)

    pattern = f"%{keyword}%"
    items: List[SearchResultItem] = []

    # 1. 搜索检验指标明细
    check_details = await db.execute(
        select(MedicalCheckDetail, MedicalCheck.medical_date)
        .join(MedicalCheck, MedicalCheckDetail.medical_id == MedicalCheck.medical_id)
        .where(
            MedicalCheck.patient_id == patient_id,
            MedicalCheckDetail.index_name.ilike(pattern),
        )
        .order_by(desc(MedicalCheck.medical_date))
        .limit(10)
    )
    for detail, med_date in check_details.all():
        items.append(SearchResultItem(
            module="check",
            id=detail.index_id or detail.medical_detail_id,
            title=f"{detail.index_name}: {detail.index_value} {detail.index_unit or ''}",
            subtitle=f"参考值: {detail.reference_value or '-'}",
            date=med_date.isoformat() if med_date else None,
        ))

    # 2. 搜索检查报告
    exams = await db.execute(
        select(MedicalExam)
        .where(
            MedicalExam.patient_id == patient_id,
            or_(
                MedicalExam.exam_type.ilike(pattern),
                MedicalExam.exam_info.ilike(pattern),
                MedicalExam.exam_diag.ilike(pattern),
            ),
        )
        .order_by(desc(MedicalExam.medical_date))
        .limit(10)
    )
    for exam in exams.scalars().all():
        items.append(SearchResultItem(
            module="exam",
            id=exam.exam_id,
            title=exam.title or exam.exam_type or "检查报告",
            subtitle=(exam.exam_diag or exam.exam_info or "")[:100],
            date=exam.medical_date.isoformat() if exam.medical_date else None,
        ))

    # 3. 搜索病理报告
    pathologies = await db.execute(
        select(PathologyReport)
        .where(
            PathologyReport.patient_id == patient_id,
            or_(
                PathologyReport.diagnosis.ilike(pattern),
                PathologyReport.cancer_type.ilike(pattern),
                PathologyReport.histology_type.ilike(pattern),
            ),
        )
        .order_by(desc(PathologyReport.report_date))
        .limit(10)
    )
    for path in pathologies.scalars().all():
        items.append(SearchResultItem(
            module="pathology",
            id=path.report_id,
            title=path.cancer_type or path.histology_type or "病理报告",
            subtitle=(path.diagnosis or "")[:100],
            date=path.report_date.isoformat() if path.report_date else None,
        ))

    # 4. 搜索用药记录
    meds = await db.execute(
        select(Medication)
        .where(
            Medication.patient_id == patient_id,
            or_(
                Medication.medication_name.ilike(pattern),
                Medication.generic_name.ilike(pattern),
            ),
        )
        .order_by(desc(Medication.start_date))
        .limit(10)
    )
    for med in meds.scalars().all():
        items.append(SearchResultItem(
            module="medication",
            id=med.id,
            title=med.medication_name,
            subtitle=f"{med.dosage or ''} {med.frequency or ''}".strip(),
            date=med.start_date.isoformat() if med.start_date else None,
        ))

    # 5. 搜索时间线事件
    events = await db.execute(
        select(TimelineEvent)
        .where(
            TimelineEvent.patient_id == patient_id,
            or_(
                TimelineEvent.title.ilike(pattern),
                TimelineEvent.description.ilike(pattern),
            ),
        )
        .order_by(desc(TimelineEvent.event_date))
        .limit(10)
    )
    for event in events.scalars().all():
        items.append(SearchResultItem(
            module="timeline",
            id=event.event_id,
            title=event.title or "时间线事件",
            subtitle=(event.description or "")[:100],
            date=event.event_date.isoformat() if event.event_date else None,
        ))

    # 按日期排序
    items.sort(key=lambda x: x.date or "", reverse=True)

    return SearchResponse(
        keyword=keyword,
        total=len(items),
        items=items[:limit],
    )
