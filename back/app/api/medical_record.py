"""病情记录 API - 病情记录 CRUD"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.medical import MedicalRecord
from app.schemas.medical import (
    MedicalRecordCreate, MedicalRecordResponse,
    MedicalRecordQuery, MedicalRecordUpdate,
)
from app.services.patient_service import PatientService

router = APIRouter()


# ============= MedicalRecord CRUD =============

@router.post("/records/query", response_model=List[MedicalRecordResponse])
async def query_medical_records(
    query: MedicalRecordQuery,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """查询病情记录"""
    await PatientService.verify_ownership(db, query.patient_id, current_user.account_id)

    result = await db.execute(
        select(MedicalRecord).where(
            MedicalRecord.patient_id == query.patient_id
        ).order_by(desc(MedicalRecord.record_date)).limit(query.limit)
    )
    return result.scalars().all()


@router.post("/records", response_model=MedicalRecordResponse)
async def create_medical_record(
    data: MedicalRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """创建病情记录"""
    await PatientService.verify_ownership(db, data.patient_id, current_user.account_id)

    record = MedicalRecord(**data.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/records/{record_id}", response_model=MedicalRecordResponse)
async def get_medical_record_detail(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取病情记录详情"""
    result = await db.execute(
        select(MedicalRecord).join(Patient).where(
            MedicalRecord.record_id == record_id,
            Patient.account_id == current_user.account_id
        )
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    return record


@router.put("/records/{record_id}", response_model=MedicalRecordResponse)
async def update_medical_record(
    record_id: int,
    data: MedicalRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """更新病情记录"""
    result = await db.execute(
        select(MedicalRecord).join(Patient).where(
            MedicalRecord.record_id == record_id,
            Patient.account_id == current_user.account_id
        )
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 仅更新提交的字段
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/records/{record_id}")
async def delete_medical_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """删除病情记录"""
    result = await db.execute(
        select(MedicalRecord).join(Patient).where(
            MedicalRecord.record_id == record_id,
            Patient.account_id == current_user.account_id
        )
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    await db.delete(record)
    await db.commit()

    return {"message": "删除成功"}