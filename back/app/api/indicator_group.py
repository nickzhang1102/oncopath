"""指标组合 API - 用户自定义指标组合 CRUD"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import LoginAccount
from app.models.medical import UserIndexGroup
from app.schemas.medical import IndexGroupCreate, IndexGroupResponse
from app.services.patient_service import PatientService

router = APIRouter()


@router.post("/indices/groups", response_model=IndexGroupResponse)
async def create_index_group(
    data: IndexGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """创建指标组合"""
    await PatientService.verify_ownership(db, data.patient_id, current_user.account_id)

    # 检查同名组合
    existing = await db.execute(
        select(UserIndexGroup).where(
            UserIndexGroup.account_id == current_user.account_id,
            UserIndexGroup.patient_id == data.patient_id,
            UserIndexGroup.group_name == data.group_name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="组合名称已存在")

    group = UserIndexGroup(
        account_id=current_user.account_id,
        patient_id=data.patient_id,
        group_name=data.group_name,
        index_ids=data.index_ids,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)

    return IndexGroupResponse(
        id=group.id,
        patient_id=group.patient_id,
        group_name=group.group_name,
        index_ids=group.index_ids,
        created_at=group.created_at,
    )


@router.get("/indices/groups", response_model=List[IndexGroupResponse])
async def list_index_groups(
    patient_id: int = Query(..., description="患者ID"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """获取患者的指标组合列表"""
    await PatientService.verify_ownership(db, patient_id, current_user.account_id)

    result = await db.execute(
        select(UserIndexGroup).where(
            UserIndexGroup.account_id == current_user.account_id,
            UserIndexGroup.patient_id == patient_id,
        ).order_by(UserIndexGroup.created_at.desc())
    )
    groups = result.scalars().all()

    return [
        IndexGroupResponse(
            id=g.id,
            patient_id=g.patient_id,
            group_name=g.group_name,
            index_ids=g.index_ids,
            created_at=g.created_at,
        )
        for g in groups
    ]


@router.delete("/indices/groups/{group_id}")
async def delete_index_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """删除指标组合"""
    result = await db.execute(
        select(UserIndexGroup).where(
            UserIndexGroup.id == group_id,
            UserIndexGroup.account_id == current_user.account_id,
        )
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="组合不存在")

    await db.delete(group)
    await db.commit()

    return {"status": "success", "message": "组合已删除"}