"""用药记录 API"""
import logging
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_

from app.core.database import get_db
from app.api.auth import get_current_user
from app.api.deps import verify_patient_access
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.medication import Medication
from app.schemas.medication import (
    MedicationCreate, MedicationUpdate, MedicationResponse,
    MedicationListResponse,
)
from app.services.consultation.summary_service import SummaryService

router = APIRouter()

logger = logging.getLogger(__name__)


async def _trigger_medication_summary(db: AsyncSession, patient_id: int, start_date, end_date):
    """用药记录变动后触发规则概要自动生成（独立事务隔离）"""
    try:
        async with db.begin_nested():
            svc = SummaryService(db)
            period_start = start_date if isinstance(start_date, date_type) else date_type.today()
            period_end = end_date if isinstance(end_date, date_type) else date_type.today()
            await svc.generate_rule_summary(
                patient_id=patient_id,
                summary_type="medication_record",
                period_start=period_start,
                period_end=period_end,
            )
        await db.commit()
    except Exception:
        await db.rollback()
        logger.warning("用药概要自动生成失败 patient_id=%s", patient_id, exc_info=True)


async def _get_medication_or_404(
    db: AsyncSession, medication_id: int, account_id: int
) -> Medication:
    """获取用药记录并验证归属"""
    result = await db.execute(
        select(Medication).join(Patient).where(
            Medication.id == medication_id,
            Patient.account_id == account_id
        )
    )
    medication = result.scalar_one_or_none()
    if not medication:
        raise HTTPException(status_code=404, detail="用药记录不存在")
    return medication


@router.get("", response_model=MedicationListResponse)
async def list_medications(
    patient_id: int = Query(..., description="患者ID"),
    status: str = Query(None, description="状态筛选: active/discontinued/completed"),
    is_ongoing: bool = Query(None, description="是否持续用药"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取患者用药记录列表"""
    await verify_patient_access(db, patient_id, current_user.account_id)

    sql = select(Medication).where(Medication.patient_id == patient_id)

    if status:
        sql = sql.where(Medication.status == status)
    if is_ongoing is not None:
        sql = sql.where(Medication.is_ongoing == is_ongoing)

    sql = sql.order_by(desc(Medication.start_date)).limit(limit).offset(offset)

    # 总数
    count_sql = select(func.count()).select_from(Medication).where(
        Medication.patient_id == patient_id
    )
    if status:
        count_sql = count_sql.where(Medication.status == status)
    if is_ongoing is not None:
        count_sql = count_sql.where(Medication.is_ongoing == is_ongoing)

    total = (await db.execute(count_sql)).scalar()

    # 活跃数量
    active_count = (await db.execute(
        select(func.count()).select_from(Medication).where(
            Medication.patient_id == patient_id,
            Medication.status == "active"
        )
    )).scalar()

    result = await db.execute(sql)
    items = result.scalars().all()

    return MedicationListResponse(
        items=items, total=total, active_count=active_count
    )


@router.post("", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
async def create_medication(
    data: MedicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """创建用药记录"""
    await verify_patient_access(db, data.patient_id, current_user.account_id)

    medication = Medication(
        **data.model_dump(),
        account_id=current_user.account_id,
    )
    db.add(medication)
    await db.commit()
    await db.refresh(medication)
    await _trigger_medication_summary(db, data.patient_id, data.start_date, data.end_date)
    return medication


@router.get("/{medication_id}", response_model=MedicationResponse)
async def get_medication(
    medication_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取单条用药记录"""
    return await _get_medication_or_404(db, medication_id, current_user.account_id)


@router.put("/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    medication_id: int,
    data: MedicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """更新用药记录"""
    medication = await _get_medication_or_404(db, medication_id, current_user.account_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(medication, field, value)

    # 如果设置了结束日期，自动更新 is_ongoing
    if data.end_date is not None and data.is_ongoing is None:
        medication.is_ongoing = False

    # 如果状态改为 discontinued 或 completed，自动更新 is_ongoing
    if data.status in ("discontinued", "completed") and data.is_ongoing is None:
        medication.is_ongoing = False

    await db.commit()
    await db.refresh(medication)
    await _trigger_medication_summary(db, medication.patient_id, medication.start_date, medication.end_date)
    return medication


@router.delete("/{medication_id}")
async def delete_medication(
    medication_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """删除用药记录"""
    medication = await _get_medication_or_404(db, medication_id, current_user.account_id)
    await db.delete(medication)
    await db.commit()
    return {"message": "删除成功"}


@router.put("/{medication_id}/discontinue", response_model=MedicationResponse)
async def discontinue_medication(
    medication_id: int,
    end_date: str = Query(None, description="结束日期(YYYY-MM-DD)"),
    reason: str = Query(None, description="停药原因"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """停药操作"""
    medication = await _get_medication_or_404(db, medication_id, current_user.account_id)

    medication.status = "discontinued"
    medication.is_ongoing = False

    if end_date:
        from datetime import datetime as dt
        medication.end_date = dt.strptime(end_date, "%Y-%m-%d").date()
    else:
        from app.utils.time_utils import get_utc_now
        medication.end_date = get_utc_now().date()

    if reason:
        existing = medication.notes or ""
        medication.notes = f"{existing}\n停药原因: {reason}".strip()

    await db.commit()
    await db.refresh(medication)
    await _trigger_medication_summary(db, medication.patient_id, medication.start_date, medication.end_date)
    return medication
