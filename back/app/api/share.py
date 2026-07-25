"""报告分享 API"""
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
from typing import Optional

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.api.auth import get_current_user
from app.models.user import LoginAccount
from app.utils.time_utils import utc_isoformat
from app.models.share_token import ShareToken
from app.models.medical import MedicalCheck, MedicalExam, PathologyReport
from app.models.patient import Patient
from app.utils.time_utils import get_utc_now, utc_isoformat

router = APIRouter(prefix="/share", tags=["报告分享"])


class ShareCreateRequest(BaseModel):
    content_type: str = Field(..., description="check_report/exam_report/pathology_report")
    content_id: int
    max_access_count: int = Field(10, ge=1, le=100)
    expire_hours: int = Field(72, ge=1, le=720)


class ShareResponse(BaseModel):
    token: str
    share_url: str
    expire_at: str


@router.post("", response_model=ShareResponse)
async def create_share_token(
    data: ShareCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """生成分享令牌"""
    # 验证内容归属
    patient_id = await _verify_content_access(
        db, data.content_type, data.content_id, current_user.account_id
    )

    token = secrets.token_urlsafe(32)
    now = get_utc_now()
    expire_at = now + timedelta(hours=data.expire_hours)
    share = ShareToken(
        token=token,
        account_id=current_user.account_id,
        patient_id=patient_id,
        content_type=data.content_type,
        content_id=data.content_id,
        max_access_count=data.max_access_count,
        expire_hours=data.expire_hours,
        expire_at=expire_at,
    )
    db.add(share)
    await db.commit()

    return ShareResponse(
        token=token,
        share_url=f"/share/report/{token}",
        expire_at=utc_isoformat(expire_at),
    )


@router.get("/report/{token}")
@limiter.limit("10/minute")
async def get_shared_report(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """通过分享令牌访问报告（无需登录）"""
    result = await db.execute(
        select(ShareToken).where(ShareToken.token == token)
    )
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="分享链接不存在")

    # 检查过期（优先使用 expire_at 冗余字段，兼容旧记录回退计算）
    effective_expire_at = share.expire_at or (share.created_at + timedelta(hours=share.expire_hours))
    if get_utc_now() > effective_expire_at:
        raise HTTPException(status_code=410, detail="分享链接已过期")

    # 检查访问次数
    if share.current_access_count >= share.max_access_count:
        raise HTTPException(status_code=410, detail="分享链接已达最大访问次数")

    # 增加访问计数
    share.current_access_count += 1
    await db.commit()

    # 获取报告数据
    report_data = await _get_report_data(db, share.content_type, share.content_id, share.patient_id)

    return {
        "content_type": share.content_type,
        "report": report_data,
    }


async def _verify_content_access(db, content_type, content_id, account_id) -> int:
    """验证内容归属，返回 patient_id"""
    if content_type == "check_report":
        result = await db.execute(select(MedicalCheck).where(MedicalCheck.medical_id == content_id))
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="报告不存在")
        # 验证患者归属
        patient_result = await db.execute(
            select(Patient).where(Patient.patient_id == item.patient_id, Patient.account_id == account_id)
        )
        if not patient_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权分享此报告")
        return item.patient_id

    elif content_type == "exam_report":
        result = await db.execute(select(MedicalExam).where(MedicalExam.exam_id == content_id))
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="报告不存在")
        patient_result = await db.execute(
            select(Patient).where(Patient.patient_id == item.patient_id, Patient.account_id == account_id)
        )
        if not patient_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权分享此报告")
        return item.patient_id

    elif content_type == "pathology_report":
        result = await db.execute(select(PathologyReport).where(PathologyReport.report_id == content_id))
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="报告不存在")
        patient_result = await db.execute(
            select(Patient).where(Patient.patient_id == item.patient_id, Patient.account_id == account_id)
        )
        if not patient_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权分享此报告")
        return item.patient_id

    else:
        raise HTTPException(status_code=400, detail="不支持的分享类型")


async def _get_report_data(db, content_type, content_id, patient_id):
    """获取报告数据（脱敏）"""
    patient_result = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
    patient = patient_result.scalar_one_or_none()

    result = {"patient_gender": patient.gender if patient else None}

    if content_type == "check_report":
        from app.models.medical import MedicalCheckDetail
        check_result = await db.execute(
            select(MedicalCheck)
            .options(selectinload(MedicalCheck.details))
            .where(MedicalCheck.medical_id == content_id)
        )
        check = check_result.scalar_one_or_none()
        if check:
            details = check.details
            result.update({
                "medical_date": utc_isoformat(check.medical_date),
                "hospital": check.hospital,
                "status": check.status,
                "interpretation": check.interpretation,
                "interpretation_at": utc_isoformat(check.interpretation_at),
                "details": [
                    {
                        "index_name": d.index_name,
                        "index_value": d.index_value,
                        "index_unit": d.index_unit,
                        "reference_value": d.reference_value,
                        "index_status": d.index_status,
                    }
                    for d in details
                ],
            })

    elif content_type == "exam_report":
        exam_result = await db.execute(select(MedicalExam).where(MedicalExam.exam_id == content_id))
        exam = exam_result.scalar_one_or_none()
        if exam:
            # 从 image_category 表查询中文名称
            exam_type_name = None
            if exam.exam_type:
                from app.models.image_report import ImageCategory
                cat_result = await db.execute(
                    select(ImageCategory).where(ImageCategory.category_key == exam.exam_type)
                )
                cat = cat_result.scalar_one_or_none()
                if cat:
                    exam_type_name = cat.category_name

            result.update({
                "medical_date": utc_isoformat(exam.medical_date),
                "hospital": exam.hospital,
                "exam_type": exam.exam_type,
                "exam_type_name": exam_type_name,
                "exam_info": exam.exam_info,
                "exam_diag": exam.exam_diag,
                "interpretation": exam.interpretation,
                "interpretation_at": utc_isoformat(exam.interpretation_at),
            })

    elif content_type == "pathology_report":
        path_result = await db.execute(
            select(PathologyReport)
            .options(selectinload(PathologyReport.ihc_markers))
            .where(PathologyReport.report_id == content_id)
        )
        path = path_result.scalar_one_or_none()
        if path:
            # 优先使用结构化 IHC 数据
            ihc_text = path.immunohistochemistry or ''
            if path.ihc_markers:
                ihc_text = ', '.join(
                    f"{m.marker_name}({m.result or '-'}{m.percentage or ''})"
                    for m in path.ihc_markers
                )
            result.update({
                "report_date": utc_isoformat(path.report_date),
                "hospital": path.hospital,
                "report_title": path.report_title,
                "comment": path.comment,
                "diagnosis": path.diagnosis,
                "cancer_type": path.cancer_type,
                "stage": path.stage,
                "histology_type": path.histology_type,
                "immunohistochemistry": ihc_text,
                "gene_testing": path.gene_testing,
                "interpretation": path.interpretation,
                "interpretation_at": utc_isoformat(path.interpretation_at),
                "ihc_markers": [
                    {"marker_name": m.marker_name, "result": m.result, "intensity": m.intensity, "percentage": m.percentage}
                    for m in path.ihc_markers
                ] if path.ihc_markers else [],
            })

    return result
