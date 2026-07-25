"""患者服务层 - 患者所有权验证与查询"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.patient import Patient


class PatientService:
    """患者业务逻辑服务"""

    @staticmethod
    async def verify_ownership(db: AsyncSession, patient_id: int, account_id: int) -> None:
        """验证患者归属当前用户，无权则抛 403

        Args:
            db: 数据库会话
            patient_id: 患者ID
            account_id: 用户账号ID

        Raises:
            HTTPException: 403 无权访问该患者
        """
        result = await db.execute(
            select(Patient).where(
                Patient.patient_id == patient_id,
                Patient.account_id == account_id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权访问该患者")

    @staticmethod
    async def get_with_ownership(db: AsyncSession, patient_id: int, account_id: int) -> Patient:
        """验证患者归属并返回 Patient 对象，无权则抛 404

        Args:
            db: 数据库会话
            patient_id: 患者ID
            account_id: 用户账号ID

        Returns:
            Patient: 患者对象

        Raises:
            HTTPException: 404 患者不存在或无权访问
        """
        result = await db.execute(
            select(Patient).where(
                Patient.patient_id == patient_id,
                Patient.account_id == account_id
            )
        )
        patient = result.scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=404, detail="患者不存在或无权访问")
        return patient


# 全局单例（便于直接调用静态方法）
patient_service = PatientService()