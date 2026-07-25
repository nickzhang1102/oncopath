"""指标历史查询 API - 用于 OCR 审查页展示历史趋势"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.medical import MedicalCheck, MedicalCheckDetail

router = APIRouter()


class IndicatorHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    index_name: str
    index_value: Optional[str]
    index_unit: Optional[str]
    index_status: Optional[str]
    reference_value: Optional[str]
    medical_date: date
    hospital: Optional[str]


class IndicatorHistoryResponse(BaseModel):
    index_name: str
    history: List[IndicatorHistoryItem]
    trend: str  # up/down/stable/unknown


@router.get("", response_model=IndicatorHistoryResponse)
async def get_indicator_history(
    patient_id: int = Query(..., description="患者ID"),
    index_name: str = Query(..., description="指标名称"),
    limit: int = Query(10, ge=1, le=50, description="历史条数"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """查询某指标的历史趋势（用于 OCR 审查页）"""
    # 验证患者归属
    patient_result = await db.execute(
        select(Patient).where(
            Patient.patient_id == patient_id,
            Patient.account_id == current_user.account_id,
        )
    )
    if not patient_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="患者不存在或无权访问")

    # 查询该指标的历史值，按日期倒序
    result = await db.execute(
        select(MedicalCheckDetail, MedicalCheck.medical_date, MedicalCheck.hospital)
        .join(MedicalCheck, MedicalCheckDetail.medical_id == MedicalCheck.medical_id)
        .where(
            MedicalCheck.patient_id == patient_id,
            MedicalCheckDetail.index_name == index_name,
        )
        .order_by(desc(MedicalCheck.medical_date))
        .limit(limit)
    )
    rows = result.all()

    history = []
    for detail, medical_date, hospital in rows:
        history.append(IndicatorHistoryItem(
            index_name=detail.index_name,
            index_value=detail.index_value,
            index_unit=detail.index_unit,
            index_status=detail.index_status,
            reference_value=detail.reference_value,
            medical_date=medical_date,
            hospital=hospital,
        ))

    # 计算趋势（基于最近两次数值）
    trend = "unknown"
    if len(history) >= 2:
        try:
            latest = float(history[0].index_value)
            previous = float(history[1].index_value)
            if latest > previous * 1.05:
                trend = "up"
            elif latest < previous * 0.95:
                trend = "down"
            else:
                trend = "stable"
        except (ValueError, TypeError, ZeroDivisionError):
            pass

    return IndicatorHistoryResponse(
        index_name=index_name,
        history=history,
        trend=trend,
    )