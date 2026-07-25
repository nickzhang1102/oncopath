"""API 公共依赖项"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.patient import Patient


async def verify_patient_access(
    db: AsyncSession,
    patient_id: int,
    account_id: int,
) -> Patient:
    """验证当前用户是否有权访问指定患者，返回 Patient 对象"""
    result = await db.execute(
        select(Patient).where(
            Patient.patient_id == patient_id,
            Patient.account_id == account_id,
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在或无权访问")
    return patient