"""医疗指标标准库 API - 指标查询、分类、收藏管理"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import LoginAccount
from app.models.medical import MedicalIndex, UserFavoriteIndex
from app.models.image_report import ImageCategory
from app.schemas.medical import (
    MedicalIndexResponse, MedicalIndexQuery,
    IndexCategoryResponse, IndexWithFavoriteResponse,
)

router = APIRouter()


# ============= MedicalIndex CRUD =============

@router.post("/indices/query", response_model=List[MedicalIndexResponse])
async def query_medical_indices(
    query: MedicalIndexQuery,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """查询医疗指标列表"""
    stmt = select(MedicalIndex)

    if query.category:
        stmt = stmt.where(MedicalIndex.category == query.category)

    stmt = stmt.order_by(MedicalIndex.sort).limit(query.limit)
    result = await db.execute(stmt)
    return result.scalars().all()


# ============= 指标分类和收藏接口 =============

@router.get("/indices/categories", response_model=List[IndexCategoryResponse])
async def get_index_categories(
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取指标分类列表（从 image_category 表读取）"""
    result = await db.execute(
        select(ImageCategory).where(
            ImageCategory.is_active == True,
        ).order_by(ImageCategory.sort_order, ImageCategory.category_key)
    )
    categories = result.scalars().all()

    # 始终在最前面添加"我的收藏"选项
    response = [{
        'category_key': 'favorites',
        'category_name': '我的收藏',
        'icon': 'star-o'
    }]

    for cat in categories:
        response.append({
            'category_key': cat.category_key,
            'category_name': cat.category_name,
            'icon': cat.icon,
            'color': cat.color
        })

    return response


@router.get("/indices/by-category", response_model=List[IndexWithFavoriteResponse])
async def get_indices_by_category(
    category: str = Query(..., description="分类key或favorites"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """按分类获取标准指标列表，标记是否已收藏"""

    # 获取用户已收藏的指标ID集合
    fav_result = await db.execute(
        select(UserFavoriteIndex.index_id).where(
            UserFavoriteIndex.account_id == current_user.account_id
        )
    )
    favorited_ids = set(fav_result.scalars().all())

    if category == 'favorites':
        # 获取收藏的指标
        result = await db.execute(
            select(MedicalIndex).join(
                UserFavoriteIndex,
                MedicalIndex.index_id == UserFavoriteIndex.index_id
            ).where(
                UserFavoriteIndex.account_id == current_user.account_id,
                MedicalIndex.is_active == True
            ).order_by(UserFavoriteIndex.sort)
        )
        indices = result.scalars().all()
    else:
        # 获取指定分类的指标
        result = await db.execute(
            select(MedicalIndex).where(
                MedicalIndex.category == category,
                MedicalIndex.is_active == True
            ).order_by(MedicalIndex.sort)
        )
        indices = result.scalars().all()

    return [{
        'index_id': idx.index_id,
        'index_code': idx.index_code,
        'index_name': idx.index_name,
        'index_unit': idx.index_unit,
        'reference_min': float(idx.reference_min) if idx.reference_min is not None else None,
        'reference_max': float(idx.reference_max) if idx.reference_max is not None else None,
        'category': idx.category,
        'description': idx.description,
        'is_chart': idx.is_chart if idx.is_chart is not None else True,
        'is_edit': idx.is_edit if idx.is_edit is not None else True,
        'is_favorited': idx.index_id in favorited_ids
    } for idx in indices]


@router.post("/indices/{index_id}/favorite")
async def add_favorite_index(
    index_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """收藏指标"""
    # 检查指标是否存在
    result = await db.execute(
        select(MedicalIndex).where(MedicalIndex.index_id == index_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="指标不存在")

    # 检查是否已收藏
    existing = await db.execute(
        select(UserFavoriteIndex).where(
            UserFavoriteIndex.account_id == current_user.account_id,
            UserFavoriteIndex.index_id == index_id
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "已收藏", "is_favorited": True}

    # 获取当前最大排序值
    max_sort = await db.execute(
        select(func.max(UserFavoriteIndex.sort)).where(
            UserFavoriteIndex.account_id == current_user.account_id
        )
    )
    next_sort = (max_sort.scalar() or 0) + 1

    # 添加收藏
    favorite = UserFavoriteIndex(
        account_id=current_user.account_id,
        index_id=index_id,
        sort=next_sort
    )
    db.add(favorite)
    await db.commit()

    return {"message": "收藏成功", "is_favorited": True}


@router.delete("/indices/{index_id}/favorite")
async def remove_favorite_index(
    index_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """取消收藏指标"""
    result = await db.execute(
        select(UserFavoriteIndex).where(
            UserFavoriteIndex.account_id == current_user.account_id,
            UserFavoriteIndex.index_id == index_id
        )
    )
    favorite = result.scalar_one_or_none()

    if not favorite:
        raise HTTPException(status_code=404, detail="未收藏此指标")

    await db.delete(favorite)
    await db.commit()

    return {"message": "取消收藏成功", "is_favorited": False}