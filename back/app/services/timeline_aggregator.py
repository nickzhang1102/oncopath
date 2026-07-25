"""
时间线聚合服务
从 timeline_events、medical_check、medical_exam、pathology_report 四张表聚合数据，
统一转换为 UnifiedTimelineItem 格式，按日期倒序合并返回。
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List, Optional
from datetime import date

from app.models.timeline import TimelineEvent
from app.models.medical import MedicalCheck, MedicalCheckDetail, MedicalExam, PathologyReport
from app.models.medication import Medication
from app.models.image_report import ImageCategory
from app.schemas.timeline import UnifiedTimelineItem, UnifiedTimelineQuery, UnifiedTimelineStats


# 来源类型 -> 图标/颜色映射
SOURCE_CONFIG = {
    "timeline_event": {"icon": "todo-list-o", "color": "#0891B2"},
    "medical_check": {"icon": "chart-trending-o", "color": "#DC2626"},
    "medical_exam": {"icon": "scan", "color": "#3B82F6"},
    "pathology_report": {"icon": "certificate", "color": "#F97316"},
    "medication": {"icon": "medic-o", "color": "#10B981"},
}

# TimelineEvent.category -> 图标/颜色映射
CATEGORY_CONFIG = {
    "chemotherapy": {"icon": "pill", "color": "#8B5CF6"},
    "radiation": {"icon": "sun", "color": "#D97706"},
    "surgery": {"icon": "knife", "color": "#DC2626"},
    "targeted": {"icon": "aim", "color": "#059669"},
    "immunotherapy": {"icon": "shield-o", "color": "#7C3AED"},
    "adc": {"icon": "aim", "color": "#EC4899"},
    "car_t": {"icon": "shield-o", "color": "#F59E0B"},
    "diagnosis": {"icon": "hospital", "color": "#0891B2"},
    "daily_status": {"icon": "todo-list-o", "color": "#0891B2"},
    "mood": {"icon": "smile-o", "color": "#059669"},
    "pain": {"icon": "warning-o", "color": "#DC2626"},
    "diet": {"icon": "gift-o", "color": "#D97706"},
    "sleep": {"icon": "closed-eye", "color": "#6366F1"},
    "stool": {"icon": "records", "color": "#6B7280"},
    "life": {"icon": "flower-o", "color": "#059669"},
}

# category 中文标签
CATEGORY_LABELS = {
    "chemotherapy": "化疗",
    "radiation": "放疗",
    "surgery": "手术",
    "targeted": "靶向治疗",
    "immunotherapy": "免疫治疗",
    "adc": "ADC治疗",
    "car_t": "CAR-T",
    "diagnosis": "诊断",
    "daily_status": "每日状态",
    "mood": "心情",
    "pain": "疼痛",
    "diet": "饮食",
    "sleep": "睡眠",
    "stool": "排便",
    "life": "生活",
    "medication_active": "用药中",
    "medication_discontinued": "已停药",
    "medication_completed": "已完成",
}


async def fetch_unified_timeline(
    db: AsyncSession,
    query: UnifiedTimelineQuery
) -> List[UnifiedTimelineItem]:
    """从5张表聚合时间线数据，按日期倒序返回

    分页策略：每张表取 offset + limit 条数据，合并排序后截取。
    对于大多数患者，单表数据量有限，此方案足够高效。
    额外加 MAX_PER_SOURCE 保护，防止单表数据极多时全表加载。
    """
    source_types = query.source_types or [
        "timeline_event", "medical_check", "medical_exam", "pathology_report",
        "medication"
    ]

    # 每张表最多取 offset + limit 条（分页窗口 + 缓冲）
    per_source_limit = query.offset + query.limit
    MAX_PER_SOURCE = 500
    if per_source_limit > MAX_PER_SOURCE:
        per_source_limit = MAX_PER_SOURCE

    items: List[UnifiedTimelineItem] = []

    if "timeline_event" in source_types:
        items.extend(await _fetch_timeline_events(db, query, per_source_limit))

    if "medical_check" in source_types:
        items.extend(await _fetch_medical_checks(db, query, per_source_limit))

    if "medical_exam" in source_types:
        items.extend(await _fetch_medical_exams(db, query, per_source_limit))

    if "pathology_report" in source_types:
        items.extend(await _fetch_pathology_reports(db, query, per_source_limit))

    if "medication" in source_types:
        items.extend(await _fetch_medications(db, query, per_source_limit))

    # 按日期倒序排列（最新在前）
    items.sort(key=lambda x: x.event_date, reverse=True)

    # 截断到 offset + limit
    return items[query.offset:query.offset + query.limit]


async def _fetch_timeline_events(
    db: AsyncSession, query: UnifiedTimelineQuery, limit: int
) -> List[UnifiedTimelineItem]:
    """查询 timeline_events 表"""
    stmt = select(TimelineEvent).where(
        TimelineEvent.patient_id == query.patient_id
    )
    if query.start_date:
        stmt = stmt.where(TimelineEvent.event_date >= query.start_date)
    if query.end_date:
        stmt = stmt.where(TimelineEvent.event_date <= query.end_date)
    stmt = stmt.order_by(desc(TimelineEvent.event_date)).limit(limit)

    result = await db.execute(stmt)
    events = result.scalars().all()

    items = []
    for e in events:
        cat_config = CATEGORY_CONFIG.get(
            e.category,
            {"icon": e.icon_type or "todo-list-o", "color": e.color_theme or "#0891B2"}
        )
        items.append(UnifiedTimelineItem(
            id=f"timeline_event:{e.event_id}",
            source_type="timeline_event",
            source_id=e.event_id,
            event_date=e.event_date,
            title=e.title,
            subtitle=(
                e.description[:50] + "..."
                if e.description and len(e.description) > 50
                else e.description
            ),
            description=e.description,
            category=e.category,
            icon=cat_config["icon"],
            color=cat_config["color"],
            extra={
                "event_type": e.event_type,
                "related_report_id": e.related_report_id,
                "medical_details": e.medical_details,
                "life_details": e.life_details,
                "category_label": CATEGORY_LABELS.get(e.category, e.category),
            },
            created_at=e.created_at,
        ))
    return items


async def _fetch_medical_checks(
    db: AsyncSession, query: UnifiedTimelineQuery, limit: int
) -> List[UnifiedTimelineItem]:
    """查询 medical_check 表，附带明细数量统计和分类信息"""
    stmt = select(MedicalCheck).where(
        MedicalCheck.patient_id == query.patient_id
    )
    if query.start_date:
        stmt = stmt.where(MedicalCheck.medical_date >= query.start_date)
    if query.end_date:
        stmt = stmt.where(MedicalCheck.medical_date <= query.end_date)
    stmt = stmt.order_by(desc(MedicalCheck.medical_date)).limit(limit)

    result = await db.execute(stmt)
    checks = result.scalars().all()

    if not checks:
        return []

    # 批量查询各 check 的 detail 数量
    check_ids = [c.medical_id for c in checks]
    detail_count_stmt = select(
        MedicalCheckDetail.medical_id,
        func.count(MedicalCheckDetail.medical_detail_id)
    ).where(
        MedicalCheckDetail.medical_id.in_(check_ids)
    ).group_by(MedicalCheckDetail.medical_id)
    count_result = await db.execute(detail_count_stmt)
    detail_counts = dict(count_result.fetchall())

    # 从 image_category 表批量查询分类名称
    category_keys = {c.category for c in checks if c.category}
    category_map: dict = {}
    if category_keys:
        cat_stmt = select(ImageCategory).where(
            ImageCategory.category_key.in_(category_keys)
        )
        cat_result = await db.execute(cat_stmt)
        for cat in cat_result.scalars().all():
            category_map[cat.category_key] = {
                "name": cat.category_name,
                "icon": cat.icon,
                "color": cat.color,
            }

    cfg = SOURCE_CONFIG["medical_check"]
    items = []
    for c in checks:
        count = detail_counts.get(c.medical_id, 0)
        cat_info = category_map.get(c.category) if c.category else None
        cat_label = cat_info["name"] if cat_info else None
        if cat_label:
            title = f"{cat_label}（{count}项）" if count else cat_label
        else:
            title = f"检验报告（{count}项）" if count else "检验报告"
        items.append(UnifiedTimelineItem(
            id=f"medical_check:{c.medical_id}",
            source_type="medical_check",
            source_id=c.medical_id,
            event_date=c.medical_date,
            title=title,
            subtitle=c.hospital,
            description=c.comment,
            category=c.category or "medical_check",
            icon=cfg["icon"],
            color=cat_info["color"] if cat_info and cat_info.get("color") else cfg["color"],
            extra={
                "details_count": count,
                "hospital": c.hospital,
                "status": c.status,
                "category_label": cat_label,
                "category_key": c.category,
                "category_icon": cat_info["icon"] if cat_info else None,
                "category_color": cat_info["color"] if cat_info else None,
            },
            created_at=c.created_at,
        ))
    return items


async def _fetch_medical_exams(
    db: AsyncSession, query: UnifiedTimelineQuery, limit: int
) -> List[UnifiedTimelineItem]:
    """查询 medical_exam 表，附带检查类型中文名称"""
    stmt = select(MedicalExam).where(
        MedicalExam.patient_id == query.patient_id
    )
    if query.start_date:
        stmt = stmt.where(MedicalExam.medical_date >= query.start_date)
    if query.end_date:
        stmt = stmt.where(MedicalExam.medical_date <= query.end_date)
    stmt = stmt.order_by(desc(MedicalExam.medical_date)).limit(limit)

    result = await db.execute(stmt)
    exams = result.scalars().all()

    if not exams:
        return []

    # 从 image_category 表批量查询检查类型中文名称
    exam_type_keys = {exam.exam_type for exam in exams if exam.exam_type}
    exam_type_map = {}
    if exam_type_keys:
        cat_stmt = select(ImageCategory).where(
            ImageCategory.category_key.in_(exam_type_keys)
        )
        cat_result = await db.execute(cat_stmt)
        for cat in cat_result.scalars().all():
            exam_type_map[cat.category_key] = {
                "name": cat.category_name,
                "icon": cat.icon,
                "color": cat.color,
            }

    cfg = SOURCE_CONFIG["medical_exam"]
    items = []
    for e in exams:
        cat_info = exam_type_map.get(e.exam_type) if e.exam_type else None
        cat_name = cat_info["name"] if cat_info else None
        title = e.title or cat_name or e.exam_type or "检查报告"
        items.append(UnifiedTimelineItem(
            id=f"medical_exam:{e.exam_id}",
            source_type="medical_exam",
            source_id=e.exam_id,
            event_date=e.medical_date,
            title=title,
            subtitle=e.hospital,
            description=e.exam_diag or e.exam_info,
            category=e.exam_type or "medical_exam",
            icon=cat_info["icon"] if cat_info and cat_info.get("icon") else cfg["icon"],
            color=cat_info["color"] if cat_info and cat_info.get("color") else cfg["color"],
            extra={
                "exam_type": e.exam_type,
                "exam_type_label": cat_name,
                "exam_info": e.exam_info,
                "exam_diag": e.exam_diag,
                "hospital": e.hospital,
            },
            created_at=e.created_at,
        ))
    return items


async def _fetch_pathology_reports(
    db: AsyncSession, query: UnifiedTimelineQuery, limit: int
) -> List[UnifiedTimelineItem]:
    """查询 pathology_report 表"""
    stmt = select(PathologyReport).where(
        PathologyReport.patient_id == query.patient_id
    )
    if query.start_date:
        stmt = stmt.where(PathologyReport.report_date >= query.start_date)
    if query.end_date:
        stmt = stmt.where(PathologyReport.report_date <= query.end_date)
    stmt = stmt.order_by(desc(PathologyReport.report_date)).limit(limit)

    result = await db.execute(stmt)
    reports = result.scalars().all()

    cfg = SOURCE_CONFIG["pathology_report"]
    items = []
    for r in reports:
        items.append(UnifiedTimelineItem(
            id=f"pathology_report:{r.report_id}",
            source_type="pathology_report",
            source_id=r.report_id,
            event_date=r.report_date,
            title=r.report_title or "病理报告",
            subtitle=r.hospital,
            description=r.comment,
            category="pathology_report",
            icon=cfg["icon"],
            color=cfg["color"],
            extra={
                "has_image": r.image_path is not None,
                "hospital": r.hospital,
            },
            created_at=r.created_at,
        ))
    return items


async def _fetch_medications(
    db: AsyncSession, query: UnifiedTimelineQuery, limit: int
) -> List[UnifiedTimelineItem]:
    """查询 medications 表"""
    stmt = select(Medication).where(
        Medication.patient_id == query.patient_id
    )
    if query.start_date:
        stmt = stmt.where(Medication.start_date >= query.start_date)
    if query.end_date:
        stmt = stmt.where(Medication.start_date <= query.end_date)
    stmt = stmt.order_by(desc(Medication.start_date)).limit(limit)

    result = await db.execute(stmt)
    meds = result.scalars().all()

    cfg = SOURCE_CONFIG["medication"]
    items = []
    for m in meds:
        dosage_parts = [x for x in [m.dosage, m.frequency] if x]
        subtitle = " · ".join(dosage_parts) if dosage_parts else None
        date_range = m.start_date.isoformat()
        if m.end_date:
            date_range += f" ~ {m.end_date.isoformat()}"
        else:
            date_range += " ~ 至今"

        items.append(UnifiedTimelineItem(
            id=f"medication:{m.id}",
            source_type="medication",
            source_id=m.id,
            event_date=m.start_date,
            title=m.medication_name,
            subtitle=subtitle,
            description=m.notes,
            category=f"medication_{m.status}",
            icon=cfg["icon"],
            color=cfg["color"],
            extra={
                "generic_name": m.generic_name,
                "dosage": m.dosage,
                "frequency": m.frequency,
                "route": m.route,
                "duration": m.duration,
                "end_date": m.end_date.isoformat() if m.end_date else None,
                "is_ongoing": m.is_ongoing,
                "status": m.status,
                "prescriber": m.prescriber,
                "hospital": m.hospital,
                "side_effects": m.side_effects,
                "date_range": date_range,
            },
            created_at=m.created_at,
        ))
    return items


async def fetch_unified_stats(
    db: AsyncSession, patient_id: int
) -> UnifiedTimelineStats:
    """统计各来源数量和日期范围"""
    # 各来源计数
    te_count = (await db.execute(
        select(func.count(TimelineEvent.event_id)).where(
            TimelineEvent.patient_id == patient_id
        )
    )).scalar() or 0

    mc_count = (await db.execute(
        select(func.count(MedicalCheck.medical_id)).where(
            MedicalCheck.patient_id == patient_id
        )
    )).scalar() or 0

    me_count = (await db.execute(
        select(func.count(MedicalExam.exam_id)).where(
            MedicalExam.patient_id == patient_id
        )
    )).scalar() or 0

    pr_count = (await db.execute(
        select(func.count(PathologyReport.report_id)).where(
            PathologyReport.patient_id == patient_id
        )
    )).scalar() or 0

    med_count = (await db.execute(
        select(func.count(Medication.id)).where(
            Medication.patient_id == patient_id
        )
    )).scalar() or 0

    # 日期范围（取四张表中最早和最晚）
    date_ranges = []

    te_date = (await db.execute(
        select(
            func.min(TimelineEvent.event_date),
            func.max(TimelineEvent.event_date),
        ).where(TimelineEvent.patient_id == patient_id)
    )).first()
    if te_date and te_date[0]:
        date_ranges.append(te_date)

    mc_date = (await db.execute(
        select(
            func.min(MedicalCheck.medical_date),
            func.max(MedicalCheck.medical_date),
        ).where(MedicalCheck.patient_id == patient_id)
    )).first()
    if mc_date and mc_date[0]:
        date_ranges.append(mc_date)

    me_date = (await db.execute(
        select(
            func.min(MedicalExam.medical_date),
            func.max(MedicalExam.medical_date),
        ).where(MedicalExam.patient_id == patient_id)
    )).first()
    if me_date and me_date[0]:
        date_ranges.append(me_date)

    pr_date = (await db.execute(
        select(
            func.min(PathologyReport.report_date),
            func.max(PathologyReport.report_date),
        ).where(PathologyReport.patient_id == patient_id)
    )).first()
    if pr_date and pr_date[0]:
        date_ranges.append(pr_date)

    med_date = (await db.execute(
        select(
            func.min(Medication.start_date),
            func.max(Medication.start_date),
        ).where(Medication.patient_id == patient_id)
    )).first()
    if med_date and med_date[0]:
        date_ranges.append(med_date)

    min_date = min(r[0] for r in date_ranges).isoformat() if date_ranges else None
    max_date = max(r[1] for r in date_ranges).isoformat() if date_ranges else None

    return UnifiedTimelineStats(
        total=te_count + mc_count + me_count + pr_count + med_count,
        by_source={
            "timeline_event": te_count,
            "medical_check": mc_count,
            "medical_exam": me_count,
            "pathology_report": pr_count,
            "medication": med_count,
        },
        date_range={"start": min_date, "end": max_date},
    )