"""服药记录 API - 用药依从性追踪"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List
from datetime import date

from app.core.database import get_db
from app.api.auth import get_current_user
from app.api.deps import verify_patient_access
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.medication import Medication
from app.models.medication_log import MedicationLog
from app.schemas.medication_log import (
    MedicationLogCreate, MedicationLogResponse, AdherenceStats,
    TodayTaskSlot, TodayTask,
)
from app.utils.time_utils import get_utc_now

router = APIRouter()

TIME_SLOTS = ["morning", "afternoon", "evening", "bedtime"]


# ========== Helpers ==========
async def _verify_medication_access(db: AsyncSession, medication_id: int, account_id: int) -> Medication:
    result = await db.execute(
        select(Medication).where(Medication.id == medication_id, Medication.account_id == account_id)
    )
    med = result.scalar_one_or_none()
    if not med:
        raise HTTPException(status_code=404, detail="用药记录不存在")
    return med


def _parse_daily_frequency(frequency: Optional[str]) -> int:
    """从频率字符串推断每日次数，默认1次"""
    if not frequency:
        return 1
    freq_lower = frequency.lower()
    for n in range(4, 0, -1):
        patterns = [f"{n}次", f"bid" if n == 2 else f"tid" if n == 3 else f"qid" if n == 4 else None]
        if any(p and p in freq_lower for p in patterns if p):
            return n
        if f"每日{n}" in freq_lower or f"每天{n}" in freq_lower:
            return n
    if "次" in freq_lower:
        import re
        m = re.search(r'(\d+)\s*次', freq_lower)
        if m:
            return min(int(m.group(1)), 4)
    return 1


# ========== Endpoints ==========
@router.post("", response_model=MedicationLogResponse, status_code=201)
async def create_log(
    data: MedicationLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """创建/更新服药打卡记录（支持每日多次，按 time_slot 区分）"""
    med = await _verify_medication_access(db, data.medication_id, current_user.account_id)

    if data.time_slot and data.time_slot not in TIME_SLOTS:
        raise HTTPException(status_code=400, detail=f"无效时段，可选值: {TIME_SLOTS}")

    # 按 (medication_id, scheduled_date, time_slot) 去重
    query = select(MedicationLog).where(
        MedicationLog.medication_id == data.medication_id,
        MedicationLog.scheduled_date == data.scheduled_date,
    )
    if data.time_slot:
        query = query.where(MedicationLog.time_slot == data.time_slot)
    else:
        # 无 time_slot 时兼容旧逻辑：按日期+无slot去重
        query = query.where(MedicationLog.time_slot.is_(None))

    existing = await db.execute(query)
    old_log = existing.scalar_one_or_none()

    if old_log:
        old_log.status = data.status
        old_log.actual_time = get_utc_now() if data.status == "taken" else None
        old_log.notes = data.notes
        await db.commit()
        await db.refresh(old_log)
        return old_log

    log = MedicationLog(
        medication_id=data.medication_id,
        patient_id=med.patient_id,
        account_id=current_user.account_id,
        scheduled_date=data.scheduled_date,
        scheduled_time=data.scheduled_time,
        time_slot=data.time_slot,
        status=data.status,
        actual_time=get_utc_now() if data.status == "taken" else None,
        notes=data.notes,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


@router.get("/today/{patient_id}", response_model=List[TodayTask])
async def get_today_tasks(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """获取今日服药任务列表（按 time_slot 展开）"""
    await verify_patient_access(db, patient_id, current_user.account_id)
    today = date.today()

    meds_result = await db.execute(
        select(Medication).where(
            Medication.patient_id == patient_id,
            Medication.status == "active",
        )
    )
    medications = meds_result.scalars().all()

    logs_result = await db.execute(
        select(MedicationLog).where(
            MedicationLog.patient_id == patient_id,
            MedicationLog.scheduled_date == today,
        )
    )
    today_logs = list(logs_result.scalars().all())

    tasks = []
    for med in medications:
        daily_count = _parse_daily_frequency(med.frequency)
        med_logs = [l for l in today_logs if l.medication_id == med.id]
        logs_by_slot = {l.time_slot: l for l in med_logs if l.time_slot}

        if daily_count <= 1:
            # 每日一次：兼容旧逻辑（无 time_slot）
            log = next((l for l in med_logs if l.time_slot is None), med_logs[0] if med_logs else None)
            slot = TodayTaskSlot(time_slot=None, status=log.status if log else None, logged=log is not None)
            tasks.append(TodayTask(
                medication_id=med.id,
                medication_name=med.medication_name,
                dosage=med.dosage,
                frequency=med.frequency,
                category=med.category,
                slots=[slot],
                logged=slot.logged,
            ))
        else:
            # 每日多次：按 time_slot 展开
            slots = []
            for i, slot_name in enumerate(TIME_SLOTS[:daily_count]):
                log = logs_by_slot.get(slot_name)
                slots.append(TodayTaskSlot(
                    time_slot=slot_name,
                    status=log.status if log else None,
                    logged=log is not None,
                ))
            tasks.append(TodayTask(
                medication_id=med.id,
                medication_name=med.medication_name,
                dosage=med.dosage,
                frequency=med.frequency,
                category=med.category,
                slots=slots,
                logged=any(s.logged for s in slots),
            ))

    return tasks


@router.get("/adherence/{patient_id}", response_model=List[AdherenceStats])
async def get_adherence_stats(
    patient_id: int,
    days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """获取用药依从性统计（按 slot 粒度计算）"""
    await verify_patient_access(db, patient_id, current_user.account_id)

    medications_result = await db.execute(
        select(Medication).where(
            Medication.patient_id == patient_id,
            Medication.status == "active",
        )
    )
    medications = medications_result.scalars().all()

    if not medications:
        return []

    med_ids = [med.id for med in medications]
    start_date = date.today() - __import__('datetime').timedelta(days=days)
    all_logs_result = await db.execute(
        select(MedicationLog).where(
            MedicationLog.medication_id.in_(med_ids),
            MedicationLog.scheduled_date >= start_date,
        )
    )
    logs_by_med: dict = {}
    for log in all_logs_result.scalars().all():
        logs_by_med.setdefault(log.medication_id, []).append(log)

    stats = []
    for med in medications:
        logs = logs_by_med.get(med.id, [])
        daily_count = _parse_daily_frequency(med.frequency)

        # 计算实际应服药天数：取统计区间与用药区间的交集
        med_start = max(med.start_date, start_date)
        med_end = min(med.end_date or date.today(), date.today()) if med.end_date else date.today()
        effective_days = max(0, (med_end - med_start).days + 1) if med_start <= med_end else 0
        total_slots = effective_days * daily_count

        taken = sum(1 for l in logs if l.status == "taken")
        skipped = sum(1 for l in logs if l.status == "skipped")
        missed = sum(1 for l in logs if l.status == "missed")
        recorded_slots = taken + skipped + missed
        unrecorded = max(0, total_slots - recorded_slots)

        stats.append(AdherenceStats(
            medication_id=med.id,
            medication_name=med.medication_name,
            total_slots=total_slots,
            taken_slots=taken,
            skipped_slots=skipped,
            missed_slots=missed,
            unrecorded_slots=unrecorded,
            adherence_rate=round(taken / recorded_slots * 100, 1) if recorded_slots > 0 else 0,
            effective_adherence=round(taken / total_slots * 100, 1) if total_slots > 0 else 0,
            recording_rate=round(recorded_slots / total_slots * 100, 1) if total_slots > 0 else 0,
        ))

    return stats
