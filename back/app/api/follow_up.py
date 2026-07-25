"""随访提醒 API"""
import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional

from app.core.database import get_db
from app.api.auth import get_current_user
from app.api.deps import verify_patient_access
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.follow_up import FollowUpReminder
from app.schemas.follow_up import (
    FollowUpReminderCreate,
    FollowUpReminderUpdate,
    FollowUpReminderResponse,
    FollowUpReminderListResponse,
)

router = APIRouter(prefix="/reminders", tags=["随访提醒"])
logger = logging.getLogger(__name__)


@router.get("", response_model=FollowUpReminderListResponse)
async def list_reminders(
    patient_id: int = Query(..., description="患者ID"),
    status: Optional[str] = Query(None, description="状态筛选"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """获取提醒列表（分页）"""
    await verify_patient_access(db, patient_id, current_user.account_id)

    base_where = [
        FollowUpReminder.patient_id == patient_id,
        FollowUpReminder.account_id == current_user.account_id,
    ]
    if status:
        base_where.append(FollowUpReminder.status == status)

    # 总数
    count_stmt = select(func.count(FollowUpReminder.id)).where(*base_where)
    total = (await db.execute(count_stmt)).scalar() or 0

    # 分页数据
    stmt = (
        select(FollowUpReminder)
        .where(*base_where)
        .order_by(FollowUpReminder.reminder_date)
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return FollowUpReminderListResponse(items=items, total=total)


@router.get("/pending", response_model=list[FollowUpReminderResponse])
async def list_pending_reminders(
    patient_id: int = Query(..., description="患者ID"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """获取待处理提醒"""
    await verify_patient_access(db, patient_id, current_user.account_id)

    result = await db.execute(
        select(FollowUpReminder).where(
            FollowUpReminder.patient_id == patient_id,
            FollowUpReminder.account_id == current_user.account_id,
            FollowUpReminder.status.in_(["pending", "sent"]),
        ).order_by(FollowUpReminder.reminder_date).limit(limit)
    )
    return result.scalars().all()


@router.post("", response_model=FollowUpReminderResponse)
async def create_reminder(
    data: FollowUpReminderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """创建提醒"""
    await verify_patient_access(db, data.patient_id, current_user.account_id)

    reminder = FollowUpReminder(
        patient_id=data.patient_id,
        account_id=current_user.account_id,
        title=data.title,
        description=data.description,
        reminder_date=data.reminder_date,
        source_type=data.source_type or "manual",
        source_id=data.source_id,
    )
    db.add(reminder)
    await db.flush()
    await db.refresh(reminder)
    await db.commit()
    return reminder


@router.put("/{reminder_id}", response_model=FollowUpReminderResponse)
async def update_reminder(
    reminder_id: int,
    data: FollowUpReminderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """更新提醒"""
    result = await db.execute(
        select(FollowUpReminder).where(
            FollowUpReminder.id == reminder_id,
            FollowUpReminder.account_id == current_user.account_id,
        )
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="提醒不存在")

    if data.title is not None:
        reminder.title = data.title
    if data.description is not None:
        reminder.description = data.description
    if data.reminder_date is not None:
        reminder.reminder_date = data.reminder_date

    await db.flush()
    await db.refresh(reminder)
    await db.commit()
    return reminder


@router.delete("/{reminder_id}")
async def delete_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """删除提醒"""
    result = await db.execute(
        select(FollowUpReminder).where(
            FollowUpReminder.id == reminder_id,
            FollowUpReminder.account_id == current_user.account_id,
        )
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="提醒不存在")

    await db.delete(reminder)
    await db.commit()
    return {"status": "success", "message": "删除成功"}


@router.put("/{reminder_id}/confirm")
async def confirm_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """确认已复查"""
    result = await db.execute(
        select(FollowUpReminder).where(
            FollowUpReminder.id == reminder_id,
            FollowUpReminder.account_id == current_user.account_id,
        )
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail="提醒不存在")

    reminder.status = "confirmed"
    await db.flush()
    await db.commit()
    return {"status": "success", "message": "已确认"}