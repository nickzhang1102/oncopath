from math import ceil
import logging
from datetime import timedelta, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, asc, desc

from app.api.auth import get_current_admin_user
from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.schemas.user import (
    AdminUserItem, AdminUserDetail,
    AdminUserStatusUpdate, AdminPasswordReset,
)
from app.utils.time_utils import utc_isoformat
from app.schemas.conversation import (
    AdminIndexCreate, AdminIndexUpdate, AdminIndexStatusToggle,
    AdminIndexSortRequest, AdminIndexImportRequest, AdminIndexItem,
    AdminIndexImportResult,
    IndexCategoryCreate, IndexCategoryUpdate, IndexCategoryItem,
    LLMConfigItem, LLMConfigUpdate, LLMConfigReloadResponse,
    LLMConfigTestRequest, LLMConfigTestResponse,
)
from app.models.medical import MedicalIndex
from app.models.image_report import ImageCategory
from app.models.admin import LLMConfig
from app.models.conversation import Conversation, LeaderSession
from app.services.desensitization import DesensitizationService
from app.services.encryption_service import encryption_service
from app.utils.time_utils import get_utc_now

logger = logging.getLogger(__name__)


def _decrypt_or_plaintext(ciphertext: str) -> str:
    """尝试解密，失败则视为明文（兼容旧数据迁移）"""
    try:
        return encryption_service.decrypt(ciphertext)
    except (ValueError, Exception):
        logger.info("LLM配置解密失败，视为明文数据（首次加密迁移）")
        return ciphertext


def _paginate(items: list, total: int, page: int, page_size: int) -> dict:
    """构造统一分页响应"""
    total_pages = ceil(total / page_size) if total > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def _apply_sort(query, sort_field: str, sort_order: str, sort_map: dict):
    """应用排序到查询"""
    col_name = sort_map.get(sort_field)
    if not col_name:
        return query
    order_func = asc if sort_order == "asc" else desc
    return query.order_by(order_func(col_name))


def _clear_ocr_indicator_cache():
    """指标变更后清除 OCR 标准库缓存"""
    try:
        from app.services.ocr.llm_ocr_parser import LLMOCRParser
        LLMOCRParser.clear_cache()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"清除OCR指标缓存失败: {e}")
from app.schemas.dashboard import (
    AdminStatsResponse,
    AdminUserStats,
    AdminConsultationStats,
    AdminIndexStats,
    AdminSystemStats,
    AdminDailyTrend,
)

router = APIRouter()


@router.get("/health")
async def health_check(
    admin_user: LoginAccount = Depends(get_current_admin_user)
):
    """管理后台健康检查（验证 admin 鉴权链路）"""
    return {
        "status": "ok",
        "admin_user": admin_user.username
    }


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """管理后台仪表盘聚合统计"""
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())

    # AsyncSession 不能在 asyncio.gather 中并发使用；这里保持单会话顺序查询。
    user_total = await db.execute(select(func.count(LoginAccount.account_id)))
    user_active = await db.execute(select(func.count(LoginAccount.account_id)).where(LoginAccount.status == "active"))
    user_inactive = await db.execute(select(func.count(LoginAccount.account_id)).where(LoginAccount.status == "inactive"))
    user_today = await db.execute(select(func.count(LoginAccount.account_id)).where(LoginAccount.created_at >= today_start))

    consul_total = await db.execute(select(func.count(LeaderSession.id)))
    consul_completed = await db.execute(select(func.count(LeaderSession.id)).where(LeaderSession.state == "completed"))
    consul_ongoing = await db.execute(select(func.count(LeaderSession.id)).where(
        LeaderSession.state.in_(["assessing", "questioning", "forming_team", "monitoring", "summarizing"])
    ))
    consul_failed = await db.execute(select(func.count(LeaderSession.id)).where(LeaderSession.state == "failed"))
    consul_today = await db.execute(select(func.count(LeaderSession.id)).where(LeaderSession.started_at >= today_start))

    index_total = await db.execute(select(func.count(MedicalIndex.index_id)))
    index_active = await db.execute(select(func.count(MedicalIndex.index_id)).where(MedicalIndex.is_active == True))
    index_inactive = await db.execute(select(func.count(MedicalIndex.index_id)).where(MedicalIndex.is_active == False))
    index_category_count = await db.execute(select(func.count(ImageCategory.category_key)).where(ImageCategory.is_active == True))

    patient_total = await db.execute(select(func.count(Patient.patient_id)))
    daily_trend_rows = await _get_daily_trend(db, today)

    return AdminStatsResponse(
        users=AdminUserStats(
            total=user_total.scalar() or 0,
            active=user_active.scalar() or 0,
            inactive=user_inactive.scalar() or 0,
            today_new=user_today.scalar() or 0,
        ),
        consultations=AdminConsultationStats(
            total=consul_total.scalar() or 0,
            completed=consul_completed.scalar() or 0,
            ongoing=consul_ongoing.scalar() or 0,
            failed=consul_failed.scalar() or 0,
            today_count=consul_today.scalar() or 0,
        ),
        indices=AdminIndexStats(
            total=index_total.scalar() or 0,
            active=index_active.scalar() or 0,
            inactive=index_inactive.scalar() or 0,
            category_count=index_category_count.scalar() or 0,
        ),
        system=AdminSystemStats(
            total_patients=patient_total.scalar() or 0,
        ),
        daily_trend=daily_trend_rows,
    )


async def _get_daily_trend(db: AsyncSession, today: date) -> list[AdminDailyTrend]:
    """近30天每日趋势 — 使用 GROUP BY 聚合查询替代循环"""
    start_date = today - timedelta(days=29)
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(today + timedelta(days=1), datetime.min.time())

    # 3 条聚合查询替代 90 次循环查询
    date_col = func.date_trunc('day', LoginAccount.created_at).label('d')
    users_q = await db.execute(
        select(date_col, func.count(LoginAccount.account_id).label('cnt'))
        .where(LoginAccount.created_at >= start_dt, LoginAccount.created_at < end_dt)
        .group_by(date_col)
    )
    users_map = {row.d.date(): row.cnt for row in users_q}

    session_date_col = func.date_trunc('day', LeaderSession.started_at).label('d')
    consult_q = await db.execute(
        select(session_date_col, func.count(LeaderSession.id).label('cnt'))
        .where(LeaderSession.started_at >= start_dt, LeaderSession.started_at < end_dt)
        .group_by(session_date_col)
    )
    consult_map = {row.d.date(): row.cnt for row in consult_q}

    trends = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        trends.append(AdminDailyTrend(
            date=d.isoformat(),
            new_users=users_map.get(d, 0),
            consultations=consult_map.get(d, 0),
        ))

    return trends


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="搜索用户名或显示名"),
    status_filter: str | None = Query(None, alias="status", description="状态筛选: active/inactive"),
    sort_by: str = Query("created_at", description="排序字段: created_at/account_name/status"),
    sort_order: str = Query("desc", description="排序方向: asc/desc"),
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """管理端用户列表（分页+搜索+状态筛选+排序）"""
    conditions = []
    if search:
        pattern = f"%{search}%"
        conditions.append(
            or_(
                LoginAccount.username.ilike(pattern),
                LoginAccount.account_name.ilike(pattern),
            )
        )
    if status_filter:
        conditions.append(LoginAccount.status == status_filter)

    where = and_(*conditions) if conditions else True

    # 总数
    count_q = select(func.count(LoginAccount.account_id)).where(where)
    total = (await db.execute(count_q)).scalar() or 0

    # 排序
    user_sort_map = {
        "created_at": LoginAccount.created_at,
        "account_name": LoginAccount.account_name,
        "status": LoginAccount.status,
    }
    sort_col = user_sort_map.get(sort_by, LoginAccount.created_at)
    order_func = asc if sort_order == "asc" else desc

    # 分页查询 + LEFT JOIN 关联统计
    offset = (page - 1) * page_size
    patient_count_cte = (
        select(
            Patient.account_id,
            func.count(Patient.patient_id).label("patient_count"),
        )
        .group_by(Patient.account_id)
        .subquery()
    )

    q = (
        select(
            LoginAccount,
            func.coalesce(patient_count_cte.c.patient_count, 0).label("patient_count"),
        )
        .outerjoin(patient_count_cte, LoginAccount.account_id == patient_count_cte.c.account_id)
        .where(where)
        .order_by(order_func(sort_col))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(q)
    rows = result.all()

    items = []
    for row in rows:
        u = row[0]
        pc = row[1]

        items.append(
            AdminUserItem(
                account_id=u.account_id,
                username=u.username,
                account_name=u.account_name,
                account_type=u.account_type,
                status=u.status,
                phone=DesensitizationService.mask_phone(u.phone) if u.phone else None,
                created_at=u.created_at,
                patient_count=pc,
            ).model_dump()
        )

    return _paginate(items, total, page, page_size)


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: int,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """管理端用户详情"""
    patient_count_sub = (
        select(
            Patient.account_id,
            func.count(Patient.patient_id).label("patient_count"),
        )
        .group_by(Patient.account_id)
        .subquery()
    )

    q = (
        select(
            LoginAccount,
            func.coalesce(patient_count_sub.c.patient_count, 0).label("patient_count"),
        )
        .outerjoin(patient_count_sub, LoginAccount.account_id == patient_count_sub.c.account_id)
        .where(LoginAccount.account_id == user_id)
    )
    result = await db.execute(q)
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    user = row[0]
    pc = row[1]

    return AdminUserDetail(
        account_id=user.account_id,
        username=user.username,
        account_name=user.account_name,
        account_type=user.account_type,
        status=user.status,
        phone=DesensitizationService.mask_phone(user.phone) if user.phone else None,
        created_at=user.created_at,
        patient_count=pc,
        email=None,
        last_login_at=None,
    ).model_dump()


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    data: AdminUserStatusUpdate,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """管理端用户启禁用"""
    if user_id == admin_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能禁用自己",
        )

    result = await db.execute(
        select(LoginAccount).where(LoginAccount.account_id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.status = data.status
    await db.commit()

    action = "启用" if data.status == "active" else "禁用"
    return {"success": True, "message": f"用户已{action}"}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    data: AdminPasswordReset,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """管理端重置用户密码"""
    result = await db.execute(
        select(LoginAccount).where(LoginAccount.account_id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.password = get_password_hash(data.new_password)
    await db.commit()

    return {"success": True, "message": "密码重置成功"}


# ===== 指标库管理 =====

@router.get("/indices")
async def list_indices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = Query(None, description="分类筛选"),
    sub_category: str | None = Query(None, description="子分类筛选"),
    is_active: bool | None = Query(None, description="启用状态筛选"),
    keyword: str | None = Query(None, description="搜索指标名或编码"),
    sort_by: str = Query("sort", description="排序字段: sort/index_name/created_at/match_count"),
    sort_order: str = Query("asc", description="排序方向: asc/desc"),
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """指标列表（分页+筛选+搜索+排序）"""
    conditions = []
    if category:
        conditions.append(MedicalIndex.category == category)
    if sub_category:
        conditions.append(MedicalIndex.sub_category == sub_category)
    if is_active is not None:
        conditions.append(MedicalIndex.is_active == is_active)
    if keyword:
        pattern = f"%{keyword}%"
        conditions.append(
            or_(
                MedicalIndex.index_name.ilike(pattern),
                MedicalIndex.index_code.ilike(pattern),
            )
        )

    where = and_(*conditions) if conditions else True

    total = (await db.execute(select(func.count(MedicalIndex.index_id)).where(where))).scalar() or 0

    # 排序
    index_sort_map = {
        "sort": MedicalIndex.sort,
        "index_name": MedicalIndex.index_name,
        "created_at": MedicalIndex.index_id,
        "match_count": MedicalIndex.match_count,
    }
    sort_col = index_sort_map.get(sort_by, MedicalIndex.sort)
    order_func = asc if sort_order == "asc" else desc

    offset = (page - 1) * page_size
    q = (
        select(MedicalIndex)
        .where(where)
        .order_by(order_func(sort_col), MedicalIndex.index_id)
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(q)
    rows = result.scalars().all()

    items = [AdminIndexItem.model_validate(idx).model_dump() for idx in rows]

    return _paginate(items, total, page, page_size)


@router.post("/indices")
async def create_index(
    data: AdminIndexCreate,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """新增指标"""
    if data.index_code:
        exists = (await db.execute(
            select(MedicalIndex.index_id).where(MedicalIndex.index_code == data.index_code)
        )).scalar_one_or_none()
        if exists:
            raise HTTPException(status_code=409, detail="指标编码已存在")

    idx = MedicalIndex(
        index_code=data.index_code,
        index_name=data.index_name,
        index_name_en=data.index_name_en,
        index_unit=data.index_unit,
        category=data.category,
        sub_category=data.sub_category,
        reference_min=data.reference_min,
        reference_max=data.reference_max,
        reference_range=data.reference_range or {},
        description=data.description,
        is_chart=data.is_chart,
        is_edit=data.is_edit,
        sort=data.sort,
        is_active=True,
        is_system=False,
        match_count=0,
    )
    db.add(idx)
    await db.commit()
    await db.refresh(idx)

    _clear_ocr_indicator_cache()
    return AdminIndexItem.model_validate(idx).model_dump()


@router.put("/indices/sort")
async def update_indices_sort(
    data: AdminIndexSortRequest,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """批量更新指标排序"""
    if not data.items:
        return {"success": True, "message": "排序已更新"}

    # 构造 CASE WHEN 批量 UPDATE，避免 N+1 查询
    from sqlalchemy import case, literal_column
    case_stmt = case(
        {item.index_id: item.sort for item in data.items},
        value=MedicalIndex.index_id,
    )
    index_ids = [item.index_id for item in data.items]
    await db.execute(
        MedicalIndex.__table__.update()
        .where(MedicalIndex.index_id.in_(index_ids))
        .values(sort=case_stmt)
    )

    await db.commit()
    _clear_ocr_indicator_cache()
    return {"success": True, "message": "排序已更新"}


@router.post("/indices/import")
async def import_indices(
    data: AdminIndexImportRequest,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """批量导入指标"""
    created = 0
    skipped = 0
    errors = []

    for i, item in enumerate(data.indices):
        # index_code 重复则跳过
        if item.index_code:
            exists = (await db.execute(
                select(MedicalIndex.index_id).where(MedicalIndex.index_code == item.index_code)
            )).scalar_one_or_none()
            if exists:
                skipped += 1
                continue

        try:
            idx = MedicalIndex(
                index_code=item.index_code,
                index_name=item.index_name,
                index_name_en=item.index_name_en,
                index_unit=item.index_unit,
                category=item.category,
                sub_category=item.sub_category,
                reference_min=item.reference_min,
                reference_max=item.reference_max,
                reference_range=item.reference_range or {},
                description=item.description,
                is_chart=item.is_chart,
                is_edit=item.is_edit,
                sort=item.sort,
                is_active=True,
                is_system=False,
                match_count=0,
            )
            db.add(idx)
            created += 1
        except Exception as e:
            errors.append(f"第 {i+1} 条: {str(e)}")

    await db.commit()

    _clear_ocr_indicator_cache()
    return AdminIndexImportResult(created=created, skipped=skipped, errors=errors).model_dump()


@router.put("/indices/{index_id}")
async def update_index(
    index_id: int,
    data: AdminIndexUpdate,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """编辑指标（仅更新提供的字段）"""
    result = await db.execute(select(MedicalIndex).where(MedicalIndex.index_id == index_id))
    idx = result.scalar_one_or_none()
    if not idx:
        raise HTTPException(status_code=404, detail="指标不存在")

    update_data = data.model_dump(exclude_unset=True)
    if "index_code" in update_data and update_data["index_code"] != idx.index_code:
        exists = (await db.execute(
            select(MedicalIndex.index_id).where(MedicalIndex.index_code == update_data["index_code"])
        )).scalar_one_or_none()
        if exists:
            raise HTTPException(status_code=409, detail="指标编码已存在")

    for key, value in update_data.items():
        setattr(idx, key, value)

    await db.commit()
    await db.refresh(idx)

    _clear_ocr_indicator_cache()
    return AdminIndexItem.model_validate(idx).model_dump()


@router.put("/indices/{index_id}/status")
async def toggle_index_status(
    index_id: int,
    data: AdminIndexStatusToggle,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """指标启禁用"""
    result = await db.execute(select(MedicalIndex).where(MedicalIndex.index_id == index_id))
    idx = result.scalar_one_or_none()
    if not idx:
        raise HTTPException(status_code=404, detail="指标不存在")

    idx.is_active = data.is_active
    await db.commit()
    await db.refresh(idx)

    _clear_ocr_indicator_cache()
    return AdminIndexItem.model_validate(idx).model_dump()


@router.delete("/indices/{index_id}")
async def delete_index(
    index_id: int,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """删除指标（仅 is_system=false）"""
    result = await db.execute(select(MedicalIndex).where(MedicalIndex.index_id == index_id))
    idx = result.scalar_one_or_none()
    if not idx:
        raise HTTPException(status_code=404, detail="指标不存在")

    if idx.is_system:
        raise HTTPException(status_code=409, detail="系统内置指标不可删除")

    await db.delete(idx)
    await db.commit()

    _clear_ocr_indicator_cache()
    return {"success": True, "message": "指标已删除"}


# ===== 指标分类管理（复用 image_category 表） =====

@router.get("/indices/categories")
async def list_index_categories(
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """指标分类列表"""
    # 查询所有分类及其 index_count
    count_sub = (
        select(
            MedicalIndex.category,
            func.count(MedicalIndex.index_id).label("index_count"),
        )
        .group_by(MedicalIndex.category)
        .subquery()
    )

    q = (
        select(
            ImageCategory,
            func.coalesce(count_sub.c.index_count, 0).label("index_count"),
        )
        .outerjoin(count_sub, ImageCategory.category_key == count_sub.c.category)
        .order_by(ImageCategory.sort_order, ImageCategory.category_key)
    )
    result = await db.execute(q)
    rows = result.all()

    items = []
    for row in rows:
        cat = row[0]
        ic = row[1]
        items.append(IndexCategoryItem(
            category_key=cat.category_key,
            category_name=cat.category_name,
            sort=cat.sort_order,
            is_active=cat.is_active,
            icon=cat.icon,
            color=cat.color,
            description=cat.description,
            group_key=cat.group_key,
            report_type=cat.report_type,
            index_count=ic,
        ).model_dump())

    return {"items": items}


@router.post("/indices/categories")
async def create_index_category(
    data: IndexCategoryCreate,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """新增指标分类"""
    exists = (await db.execute(
        select(ImageCategory.category_key).where(ImageCategory.category_key == data.category_key)
    )).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="分类键已存在")

    cat = ImageCategory(
        category_key=data.category_key,
        category_name=data.category_name,
        sort_order=data.sort or 0,
        is_active=True,
        icon=data.icon,
        color=data.color,
        description=data.description,
        group_key=data.group_key,
        report_type=data.report_type,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)

    _clear_ocr_indicator_cache()
    return IndexCategoryItem(
        category_key=cat.category_key,
        category_name=cat.category_name,
        sort=cat.sort_order,
        is_active=cat.is_active,
        icon=cat.icon,
        color=cat.color,
        description=cat.description,
        group_key=cat.group_key,
        report_type=cat.report_type,
        index_count=0,
    ).model_dump()


@router.put("/indices/categories/{category_key}")
async def update_index_category(
    category_key: str,
    data: IndexCategoryUpdate,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """编辑指标分类"""
    result = await db.execute(select(ImageCategory).where(ImageCategory.category_key == category_key))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")

    update_data = data.model_dump(exclude_unset=True)
    # 映射 sort -> sort_order
    if "sort" in update_data:
        update_data["sort_order"] = update_data.pop("sort")
    for key, value in update_data.items():
        setattr(cat, key, value)

    await db.commit()
    await db.refresh(cat)

    _clear_ocr_indicator_cache()
    # 统计指标数
    ic = (await db.execute(
        select(func.count(MedicalIndex.index_id)).where(MedicalIndex.category == category_key)
    )).scalar() or 0

    return IndexCategoryItem(
        category_key=cat.category_key,
        category_name=cat.category_name,
        sort=cat.sort_order,
        is_active=cat.is_active,
        icon=cat.icon,
        color=cat.color,
        description=cat.description,
        group_key=cat.group_key,
        report_type=cat.report_type,
        index_count=ic,
    ).model_dump()


@router.delete("/indices/categories/{category_key}")
async def delete_index_category(
    category_key: str,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """删除指标分类（有指标引用时拒绝）"""
    result = await db.execute(select(ImageCategory).where(ImageCategory.category_key == category_key))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")

    # 检查是否有指标引用
    ref_count = (await db.execute(
        select(func.count(MedicalIndex.index_id)).where(MedicalIndex.category == category_key)
    )).scalar() or 0

    if ref_count > 0:
        raise HTTPException(status_code=409, detail=f"该分类下有 {ref_count} 个指标，无法删除")

    # 检查是否有报告引用
    from app.models.image_report import ImageReport
    img_count = (await db.execute(
        select(func.count(ImageReport.report_id)).where(ImageReport.category == category_key)
    )).scalar() or 0

    if img_count > 0:
        raise HTTPException(status_code=409, detail=f"该分类下有 {img_count} 个报告，无法删除")

    await db.delete(cat)
    await db.commit()

    _clear_ocr_indicator_cache()
    return {"success": True, "message": "分类已删除"}


# ===== LLM 配置管理 =====

def _mask_secret_value(value: str) -> str:
    """敏感字段掩码：显示后4位"""
    if not value or len(value) <= 4:
        return "****"
    return f"****{value[-4:]}"


@router.get("/llm-configs")
async def list_llm_configs(
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有 LLM 配置

    表无记录 → 从 .env (Settings) 构造展示列表，is_active=False
    表有记录 → 用表记录；is_active=False 时展示 .env 值，is_active=True 时展示数据库值
    """
    from app.services.llm_config_service import LLMConfigService, LLM_CONFIG_DEFINITIONS

    result = await db.execute(
        select(LLMConfig).order_by(LLMConfig.config_group, LLMConfig.id)
    )
    configs = result.scalars().all()
    config_map = {cfg.config_key: cfg for cfg in configs}

    items = []
    needs_migration = False
    for config_key, group, display_name, description, is_secret in LLM_CONFIG_DEFINITIONS:
        cfg = config_map.get(config_key)
        if cfg:
            # 表中有记录
            if cfg.is_active:
                if cfg.is_secret:
                    raw_value = _decrypt_or_plaintext(cfg.config_value)
                    # 明文旧数据自动迁移：解密失败说明是明文，加密后回写
                    if raw_value == cfg.config_value and cfg.config_value:
                        cfg.config_value = encryption_service.encrypt(cfg.config_value)
                        needs_migration = True
                else:
                    raw_value = cfg.config_value
            else:
                raw_value = LLMConfigService.get_effective_value(config_key)
            items.append(LLMConfigItem(
                id=cfg.id,
                config_key=cfg.config_key,
                config_value=_mask_secret_value(raw_value) if is_secret and raw_value else raw_value,
                config_group=cfg.config_group,
                display_name=cfg.display_name,
                description=cfg.description,
                is_secret=cfg.is_secret,
                is_active=cfg.is_active,
                updated_at=cfg.updated_at,
            ).model_dump())
        else:
            # 表中无记录，从 .env 读取
            raw_value = LLMConfigService.get_effective_value(config_key)
            items.append(LLMConfigItem(
                id=0,
                config_key=config_key,
                config_value=_mask_secret_value(raw_value) if is_secret and raw_value else raw_value,
                config_group=group,
                display_name=display_name,
                description=description,
                is_secret=is_secret,
                is_active=False,
                updated_at=None,
            ).model_dump())

    # 自动迁移：将明文 secret 配置加密存储
    if needs_migration:
        await db.commit()
        logger.info("已自动迁移明文 secret 配置为加密存储")

    return {"items": items}


@router.put("/llm-configs/{config_key}")
async def update_llm_config(
    config_key: str,
    data: LLMConfigUpdate,
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """更新单个 LLM 配置（记录不存在时自动创建）"""
    from app.services.llm_config_service import LLM_CONFIG_DEFINITIONS

    result = await db.execute(
        select(LLMConfig).where(LLMConfig.config_key == config_key)
    )
    cfg = result.scalar_one_or_none()

    if not cfg:
        # 记录不存在，查找元数据并创建
        meta = next((d for d in LLM_CONFIG_DEFINITIONS if d[0] == config_key), None)
        if not meta:
            raise HTTPException(status_code=404, detail="未知配置项")
        _, group, display_name, description, is_secret = meta
        stored_value = encryption_service.encrypt(data.config_value) if is_secret else data.config_value
        cfg = LLMConfig(
            config_key=config_key,
            config_value=stored_value,
            config_group=group,
            display_name=display_name,
            description=description,
            is_secret=is_secret,
            is_active=True,
        )
        db.add(cfg)
    else:
        # 掩码值跳过更新
        if cfg.is_secret and data.config_value.startswith("****"):
            pass  # 不更新 config_value
        else:
            stored_value = encryption_service.encrypt(data.config_value) if cfg.is_secret else data.config_value
            cfg.config_value = stored_value
        cfg.is_active = True

    await db.commit()
    await db.refresh(cfg)

    raw = _decrypt_or_plaintext(cfg.config_value) if cfg.is_secret and cfg.config_value else cfg.config_value
    value = _mask_secret_value(raw) if cfg.is_secret and raw else raw
    return LLMConfigItem(
        id=cfg.id,
        config_key=cfg.config_key,
        config_value=value,
        config_group=cfg.config_group,
        display_name=cfg.display_name,
        description=cfg.description,
        is_secret=cfg.is_secret,
        is_active=cfg.is_active,
        updated_at=cfg.updated_at,
    ).model_dump()


@router.post("/llm-configs/reload", response_model=LLMConfigReloadResponse)
async def reload_llm_configs(
    admin_user: LoginAccount = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """重载 LLM 配置到运行时"""
    from app.services.llm_config_service import LLMConfigService

    result = await db.execute(
        select(LLMConfig).where(LLMConfig.is_active == True)
    )
    active_configs = result.scalars().all()

    if not active_configs:
        return LLMConfigReloadResponse(
            success=True,
            message="无活跃配置，使用环境变量",
            reloaded_groups=[],
        )

    # 按 config_group 分组
    groups = list(set(c.config_group for c in active_configs))

    service = LLMConfigService()
    service.apply_configs(active_configs)

    return LLMConfigReloadResponse(
        success=True,
        message=f"配置已重载，{len(groups)}个服务将使用新配置",
        reloaded_groups=sorted(groups),
    )


@router.post("/llm-configs/test", response_model=LLMConfigTestResponse)
async def test_llm_config(
    data: LLMConfigTestRequest,
    admin_user: LoginAccount = Depends(get_current_admin_user),
):
    """测试指定配置组的 LLM 连通性"""
    from app.services.llm_config_service import LLMConfigService

    result = await LLMConfigService.test_group(data.group)
    return LLMConfigTestResponse(**result)
