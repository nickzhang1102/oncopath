import logging
from datetime import date as date_type, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List

from app.core.database import get_db
from app.api.auth import get_current_user
from app.api.deps import verify_patient_access
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.timeline import TimelineEvent
from app.schemas.timeline import (
    TimelineEventCreate, TimelineEventUpdate, TimelineEventResponse,
    TimelineQuery, TimelineStats,
    UnifiedTimelineQuery, UnifiedTimelineItem, UnifiedTimelineStats,
)
from app.services.timeline_aggregator import fetch_unified_timeline, fetch_unified_stats
from app.services.consultation.summary_service import SummaryService, TREATMENT_CATEGORIES

router = APIRouter()

logger = logging.getLogger(__name__)


async def _trigger_treatment_summary(db: AsyncSession, patient_id: int, event_date, category: str):
    """治疗类事件变动后触发规则概要自动生成（独立事务隔离）"""
    if category not in TREATMENT_CATEGORIES:
        return
    try:
        async with db.begin_nested():
            svc = SummaryService(db)
            d = event_date if isinstance(event_date, date_type) else date_type.today()
            # 以事件日期所在季度为概要时段
            quarter_start = date_type(d.year, (d.month - 1) // 3 * 3 + 1, 1)
            if d.month >= 10:
                quarter_end = date_type(d.year, 12, 31)
            else:
                quarter_end = date_type(d.year, (d.month - 1) // 3 * 3 + 4, 1)
                quarter_end = quarter_end - timedelta(days=1)
            await svc.generate_rule_summary(
                patient_id=patient_id,
                summary_type="treatment",
                period_start=quarter_start,
                period_end=quarter_end,
            )
        await db.commit()
    except Exception:
        await db.rollback()
        logger.warning("治疗概要自动生成失败 patient_id=%s category=%s", patient_id, category, exc_info=True)


# ========== 原有时间线事件接口（保留兼容） ==========

@router.post("/events/query", response_model=List[TimelineEventResponse])
async def query_timeline_events(
    query: TimelineQuery,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """查询时间线事件"""
    await verify_patient_access(db, query.patient_id, current_user.account_id)

    sql = select(TimelineEvent).where(
        TimelineEvent.patient_id == query.patient_id
    )

    if query.event_type:
        sql = sql.where(TimelineEvent.event_type == query.event_type)
    if query.category:
        sql = sql.where(TimelineEvent.category == query.category)
    if query.start_date:
        sql = sql.where(TimelineEvent.event_date >= query.start_date)
    if query.end_date:
        sql = sql.where(TimelineEvent.event_date <= query.end_date)

    sql = sql.order_by(desc(TimelineEvent.event_date))
    sql = sql.limit(query.limit)

    result = await db.execute(sql)
    return result.scalars().all()

@router.post("/events", response_model=TimelineEventResponse)
async def create_timeline_event(
    data: TimelineEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """创建时间线事件"""
    await verify_patient_access(db, data.patient_id, current_user.account_id)

    event = TimelineEvent(**data.model_dump())
    db.add(event)
    await db.commit()
    await db.refresh(event)
    await _trigger_treatment_summary(db, data.patient_id, data.event_date, data.category)
    return event

@router.put("/events/{event_id}", response_model=TimelineEventResponse)
async def update_timeline_event(
    event_id: int,
    data: TimelineEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """更新时间线事件"""
    result = await db.execute(
        select(TimelineEvent).join(Patient).where(
            TimelineEvent.event_id == event_id,
            Patient.account_id == current_user.account_id
        )
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)
    await _trigger_treatment_summary(db, event.patient_id, event.event_date, event.category)
    return event

@router.delete("/events/{event_id}")
async def delete_timeline_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """删除时间线事件"""
    result = await db.execute(
        select(TimelineEvent).join(Patient).where(
            TimelineEvent.event_id == event_id,
            Patient.account_id == current_user.account_id
        )
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")

    await db.delete(event)
    await db.commit()
    await _trigger_treatment_summary(db, event.patient_id, event.event_date, event.category)
    return {"message": "删除成功"}

@router.get("/stats/{patient_id}", response_model=TimelineStats)
async def get_timeline_stats(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取时间线统计"""
    await verify_patient_access(db, patient_id, current_user.account_id)

    # 统计总数
    total_result = await db.execute(
        select(func.count(TimelineEvent.event_id)).where(
            TimelineEvent.patient_id == patient_id
        )
    )
    total_events = total_result.scalar()

    # 统计医疗事件
    medical_result = await db.execute(
        select(func.count(TimelineEvent.event_id)).where(
            TimelineEvent.patient_id == patient_id,
            TimelineEvent.event_type == "medical"
        )
    )
    medical_events = medical_result.scalar()

    # 统计生活事件
    life_events = total_events - medical_events

    # 统计分类
    category_result = await db.execute(
        select(TimelineEvent.category, func.count(TimelineEvent.event_id))
        .where(TimelineEvent.patient_id == patient_id)
        .group_by(TimelineEvent.category)
    )
    categories = {row[0]: row[1] for row in category_result.fetchall()}

    # 日期范围
    date_result = await db.execute(
        select(
            func.min(TimelineEvent.event_date),
            func.max(TimelineEvent.event_date)
        ).where(TimelineEvent.patient_id == patient_id)
    )
    min_date, max_date = date_result.fetchone()

    return TimelineStats(
        total_events=total_events,
        medical_events=medical_events,
        life_events=life_events,
        categories=categories,
        date_range={
            "start": min_date.isoformat() if min_date else None,
            "end": max_date.isoformat() if max_date else None
        }
    )


# ========== 统一时间线接口（聚合多来源） ==========

@router.post("/unified/query", response_model=List[UnifiedTimelineItem])
async def query_unified_timeline(
    query: UnifiedTimelineQuery,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """查询统一时间线（聚合时间线事件 + 检验报告 + 检查报告 + 病理报告）"""
    await verify_patient_access(db, query.patient_id, current_user.account_id)
    return await fetch_unified_timeline(db, query)


@router.get("/unified/stats/{patient_id}", response_model=UnifiedTimelineStats)
async def get_unified_stats(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取统一时间线统计（含各来源数量）"""
    await verify_patient_access(db, patient_id, current_user.account_id)
    return await fetch_unified_stats(db, patient_id)
