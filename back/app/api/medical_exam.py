"""检查报告 API - MedicalExam CRUD + AI解读"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List
import logging

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.medical import MedicalExam
from app.models.image_report import ImageReport, ImageCategory
from app.schemas.medical import (
    MedicalExamCreate, MedicalExamResponse, MedicalExamQuery, MedicalExamUpdate,
)
from app.services.interpretation_service import InterpretationService
from app.services.patient_service import PatientService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/exams/query")
async def query_medical_exams(
    query: MedicalExamQuery,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """查询检查报告"""
    await PatientService.verify_ownership(db, query.patient_id, current_user.account_id)

    stmt = select(MedicalExam).where(
        MedicalExam.patient_id == query.patient_id
    )

    if query.exam_type:
        stmt = stmt.where(MedicalExam.exam_type == query.exam_type)

    stmt = stmt.order_by(desc(MedicalExam.medical_date))
    stmt = stmt.offset(query.offset).limit(query.limit)

    result = await db.execute(stmt)
    exams = result.scalars().all()

    # 关联查询 image_report 获取 image_report_id (批量查询，避免 N+1)
    exam_ids = [exam.exam_id for exam in exams]

    image_result = await db.execute(
        select(ImageReport.report_id, ImageReport.related_exam_id).where(
            ImageReport.related_exam_id.in_(exam_ids)
        )
    )
    image_map = {row.related_exam_id: row.report_id for row in image_result.all()}

    # 从 image_category 表批量查询检查类型中文名称
    exam_type_keys = {exam.exam_type for exam in exams if exam.exam_type}
    exam_type_name_map = {}
    if exam_type_keys:
        cat_stmt = select(ImageCategory).where(
            ImageCategory.category_key.in_(exam_type_keys)
        )
        cat_result = await db.execute(cat_stmt)
        exam_type_name_map = {cat.category_key: cat.category_name for cat in cat_result.scalars().all()}

    response_list = []
    for exam in exams:
        exam_dict = {
            'exam_id': exam.exam_id,
            'patient_id': exam.patient_id,
            'medical_date': exam.medical_date,
            'hospital': exam.hospital,
            'title': exam.title,
            'exam_type': exam.exam_type,
            'exam_type_name': exam_type_name_map.get(exam.exam_type) if exam.exam_type else None,
            'exam_info': exam.exam_info,
            'exam_diag': exam.exam_diag,
            'comment': exam.comment,
            'image_report_id': image_map.get(exam.exam_id),
            'interpretation': exam.interpretation,
            'interpretation_at': exam.interpretation_at.isoformat() if exam.interpretation_at else None,
        }
        response_list.append(exam_dict)

    return response_list


@router.post("/exams", response_model=MedicalExamResponse)
async def create_medical_exam(
    data: MedicalExamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """创建检查报告"""
    await PatientService.verify_ownership(db, data.patient_id, current_user.account_id)

    exam = MedicalExam(**data.model_dump())
    db.add(exam)
    await db.commit()
    await db.refresh(exam)
    return exam


@router.get("/exams/{exam_id}")
async def get_medical_exam_detail(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取检查报告详情"""
    result = await db.execute(
        select(MedicalExam).join(Patient).where(
            MedicalExam.exam_id == exam_id,
            Patient.account_id == current_user.account_id
        )
    )
    exam = result.scalar_one_or_none()

    if not exam:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 查询关联的 image_report_id
    image_result = await db.execute(
        select(ImageReport.report_id).where(
            ImageReport.related_exam_id == exam_id
        )
    )
    image_report_id = image_result.scalar_one_or_none()

    exam_data = MedicalExamResponse.model_validate(exam).model_dump()
    exam_data['image_report_id'] = image_report_id
    return MedicalExamResponse(**exam_data)


@router.delete("/exams/{exam_id}")
async def delete_medical_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """删除检查报告"""
    result = await db.execute(
        select(MedicalExam).join(Patient).where(
            MedicalExam.exam_id == exam_id,
            Patient.account_id == current_user.account_id
        )
    )
    exam = result.scalar_one_or_none()

    if not exam:
        raise HTTPException(status_code=404, detail="记录不存在")

    await db.delete(exam)
    await db.commit()

    return {"message": "删除成功"}


@router.put("/exams/{exam_id}", response_model=MedicalExamResponse)
async def update_medical_exam(
    exam_id: int,
    data: MedicalExamUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """更新检查报告"""
    result = await db.execute(
        select(MedicalExam).join(Patient).where(
            MedicalExam.exam_id == exam_id,
            Patient.account_id == current_user.account_id
        )
    )
    exam = result.scalar_one_or_none()

    if not exam:
        raise HTTPException(status_code=404, detail="记录不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(exam, field, value)

    await db.commit()
    await db.refresh(exam)
    return exam


# ============= AI 解读 =============

@router.post("/exams/{exam_id}/interpret")
async def interpret_medical_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """生成 AI 检查报告解读"""
    # 验证报告归属
    result = await db.execute(
        select(MedicalExam).join(Patient).where(
            MedicalExam.exam_id == exam_id,
            Patient.account_id == current_user.account_id,
        )
    )
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="检查报告不存在")

    try:
        service = InterpretationService(db)
        result = await service.interpret_exam(exam_id, current_user.account_id)
        await db.commit()
        return {"status": "success", "data": result}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"检查报告AI解读失败: {e}")
        raise HTTPException(status_code=500, detail="AI解读生成失败，请稍后重试")


@router.get("/exams/{exam_id}/interpretation")
async def get_medical_exam_interpretation(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """获取检查报告已有 AI 解读"""
    result = await db.execute(
        select(MedicalExam).join(Patient).where(
            MedicalExam.exam_id == exam_id,
            Patient.account_id == current_user.account_id,
        )
    )
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="检查报告不存在")

    if not exam.interpretation:
        return {"status": "success", "data": None}

    return {
        "status": "success",
        "data": {
            "interpretation": exam.interpretation,
            "interpretation_at": exam.interpretation_at.isoformat()
            if exam.interpretation_at
            else None,
        },
    }
