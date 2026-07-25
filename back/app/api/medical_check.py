"""检验报告 API - MedicalCheck CRUD + AI解读 + 明细操作"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, delete
from sqlalchemy.orm import selectinload
from datetime import date
from typing import List
from datetime import datetime as dt
import logging

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.medical import MedicalCheck, MedicalCheckDetail, MedicalIndex
from app.schemas.medical import (
    MedicalCheckCreate, MedicalCheckResponse, MedicalCheckQuery,
    MedicalCheckDetailCreate, MedicalCheckDetailResponse,
    ManualCheckDetailCreate, MedicalCheckCommentUpdate,
)
from app.services.interpretation_service import InterpretationService
from app.services.patient_service import PatientService
from app.services.cache_service import category_cache_service

router = APIRouter()
logger = logging.getLogger(__name__)


# ============= MedicalCheck CRUD =============

@router.post("/checks/query", response_model=List[MedicalCheckResponse])
async def query_medical_checks(
    query: MedicalCheckQuery,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """查询医疗检查记录"""
    await PatientService.verify_ownership(db, query.patient_id, current_user.account_id)

    stmt = select(MedicalCheck).options(
        selectinload(MedicalCheck.details).selectinload(MedicalCheckDetail.standard_index)
    ).where(
        MedicalCheck.patient_id == query.patient_id
    )

    if query.start_date:
        stmt = stmt.where(MedicalCheck.medical_date >= query.start_date)
    if query.end_date:
        stmt = stmt.where(MedicalCheck.medical_date <= query.end_date)
    if query.category:
        stmt = stmt.where(MedicalCheck.category == query.category)

    stmt = stmt.order_by(desc(MedicalCheck.medical_date))
    stmt = stmt.offset(query.offset).limit(query.limit)

    result = await db.execute(stmt)
    checks = result.scalars().all()

    # 批量查询分类信息（带缓存）
    cat_map = await category_cache_service.get_category_map(db)

    # details 已通过 selectinload 预加载，无需额外查询
    response_list = []
    for check in checks:
        check_dict = MedicalCheckResponse.model_validate(check).model_dump()
        detail_dicts = []
        for d in check.details:
            detail_dict = MedicalCheckDetailResponse.model_validate(d).model_dump()
            # 从关联的 standard_index 提取 category
            if d.standard_index and d.standard_index.category:
                detail_dict['category'] = d.standard_index.category
            detail_dicts.append(detail_dict)
        check_dict['details'] = detail_dicts
        # 注入分类可视化信息
        if check.category and check.category in cat_map:
            cat_info = cat_map[check.category]
            check_dict['category_name'] = cat_info.get('category_name')
            check_dict['category_icon'] = cat_info.get('icon')
            check_dict['category_color'] = cat_info.get('color')
        response_list.append(MedicalCheckResponse(**check_dict))

    return response_list


@router.post("/checks", response_model=MedicalCheckResponse)
async def create_medical_check(
    data: MedicalCheckCreate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """创建医疗检查记录"""
    await PatientService.verify_ownership(db, data.patient_id, current_user.account_id)

    # 创建检查记录
    check = MedicalCheck(
        patient_id=data.patient_id,
        medical_date=data.medical_date,
        hospital=data.hospital,
        comment=data.comment
    )
    db.add(check)
    await db.flush()  # 获取medical_id

    # 创建明细
    details_list = []
    for detail_data in data.details:
        detail = MedicalCheckDetail(
            medical_id=check.medical_id,
            **detail_data.model_dump()
        )
        db.add(detail)
        details_list.append(detail)

    await db.commit()
    await db.refresh(check)

    # 刷新所有明细
    for detail in details_list:
        await db.refresh(detail)

    # 手动构建响应字典，避免异步加载问题
    check_dict = {
        'medical_id': check.medical_id,
        'patient_id': check.patient_id,
        'medical_date': check.medical_date,
        'hospital': check.hospital,
        'comment': check.comment,
        'status': check.status,
        'created_at': check.created_at,
        'details': [{
            'medical_detail_id': d.medical_detail_id,
            'medical_id': d.medical_id,
            'index_id': getattr(d, 'index_id', None),
            'index_name': d.index_name,
            'index_value': d.index_value,
            'index_unit': d.index_unit,
            'reference_value': d.reference_value,
            'index_status': d.index_status
        } for d in details_list]
    }
    return MedicalCheckResponse(**check_dict)


@router.get("/checks/{medical_id}", response_model=MedicalCheckResponse)
async def get_medical_check_detail(
    medical_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取检验报告详情"""
    result = await db.execute(
        select(MedicalCheck).options(
            selectinload(MedicalCheck.details)
        ).join(Patient).where(
            MedicalCheck.medical_id == medical_id,
            Patient.account_id == current_user.account_id
        )
    )
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 构建响应
    check_dict = MedicalCheckResponse.model_validate(check).model_dump()
    check_dict['details'] = [MedicalCheckDetailResponse.model_validate(d).model_dump() for d in check.details]
    return MedicalCheckResponse(**check_dict)


@router.delete("/checks/{medical_id}")
async def delete_medical_check(
    medical_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """删除医疗检查记录"""
    # 查询并验证权限
    result = await db.execute(
        select(MedicalCheck).join(Patient).where(
            MedicalCheck.medical_id == medical_id,
            Patient.account_id == current_user.account_id
        )
    )
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="记录不存在")

    await db.delete(check)
    await db.commit()

    return {"message": "删除成功"}


# ============= 指标明细操作 =============

@router.post("/checks/detail")
async def add_medical_check_detail(
    data: ManualCheckDetailCreate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """添加检验明细（支持用户手动添加指标数据）"""
    # 验证患者权限
    patient_id = data.patient_id
    if patient_id:
        await PatientService.verify_ownership(db, patient_id, current_user.account_id)
    else:
        # 获取用户默认患者
        patient_result = await db.execute(
            select(Patient).where(Patient.account_id == current_user.account_id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=404, detail="未找到患者")
        patient_id = patient.patient_id

    # 解析日期
    medical_date = data.medical_date
    if isinstance(medical_date, str):
        medical_date = dt.strptime(medical_date, '%Y-%m-%d').date()

    # 检查是否已存在相同日期的检查记录
    check_result = await db.execute(
        select(MedicalCheck).where(
            MedicalCheck.patient_id == patient_id,
            MedicalCheck.medical_date == medical_date,
            MedicalCheck.hospital == (data.hospital or '居家测量')
        )
    )
    check = check_result.scalar_one_or_none()

    if not check:
        # 创建新的检查记录
        check = MedicalCheck(
            patient_id=patient_id,
            medical_date=medical_date,
            hospital=data.hospital or '居家测量',
            comment=''
        )
        db.add(check)
        await db.flush()

    # 检查是否已存在相同指标
    existing_detail = await db.execute(
        select(MedicalCheckDetail).where(
            MedicalCheckDetail.medical_id == check.medical_id,
            MedicalCheckDetail.index_name == data.index_name
        )
    )
    if existing_detail.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该日期已存在此指标记录")

    # 创建明细
    detail = MedicalCheckDetail(
        medical_id=check.medical_id,
        index_id=data.index_id,
        index_name=data.index_name,
        index_value=data.index_value,
        index_unit=data.index_unit,
        reference_value=data.reference_value,
        index_status=data.index_status or 'normal'
    )
    db.add(detail)
    await db.commit()
    await db.refresh(detail)

    return {
        "status": "success",
        "message": "添加成功",
        "data": {
            "medical_id": check.medical_id,
            "medical_detail_id": detail.medical_detail_id
        }
    }


@router.put("/checks/{medical_id}/comment")
async def update_medical_check_comment(
    medical_id: int,
    data: MedicalCheckCommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """更新检验备注"""
    result = await db.execute(
        select(MedicalCheck).join(Patient).where(
            MedicalCheck.medical_id == medical_id,
            Patient.account_id == current_user.account_id
        )
    )
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(status_code=404, detail="记录不存在")

    check.comment = data.comment or ''
    await db.commit()

    return {"status": "success", "message": "更新成功"}


@router.delete("/checks/details/{detail_id}")
async def delete_medical_check_detail(
    detail_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """删除检验明细"""
    result = await db.execute(
        select(MedicalCheckDetail).join(MedicalCheck).join(Patient).where(
            MedicalCheckDetail.medical_detail_id == detail_id,
            Patient.account_id == current_user.account_id
        )
    )
    detail = result.scalar_one_or_none()

    if not detail:
        raise HTTPException(status_code=404, detail="记录不存在")

    await db.delete(detail)
    await db.commit()

    return {"status": "success", "message": "删除成功"}


# ============= AI 解读 =============

@router.post("/checks/{medical_id}/interpret")
async def interpret_medical_check(
    medical_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """生成 AI 检验报告解读"""
    # 验证报告归属
    result = await db.execute(
        select(MedicalCheck).join(Patient).where(
            MedicalCheck.medical_id == medical_id,
            Patient.account_id == current_user.account_id,
        )
    )
    check = result.scalar_one_or_none()
    if not check:
        raise HTTPException(status_code=404, detail="检验报告不存在")

    try:
        from app.services.interpretation_service import InterpretationService
        service = InterpretationService(db)
        result = await service.interpret_check(medical_id, current_user.account_id)
        await db.commit()
        return {"status": "success", "data": result}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"AI解读失败: {e}")
        raise HTTPException(status_code=500, detail="AI解读生成失败，请稍后重试")


@router.get("/checks/{medical_id}/interpretation")
async def get_medical_check_interpretation(
    medical_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """获取已有 AI 解读"""
    # 验证报告归属
    result = await db.execute(
        select(MedicalCheck).join(Patient).where(
            MedicalCheck.medical_id == medical_id,
            Patient.account_id == current_user.account_id,
        )
    )
    check = result.scalar_one_or_none()
    if not check:
        raise HTTPException(status_code=404, detail="检验报告不存在")

    if not check.interpretation:
        return {"status": "success", "data": None}

    return {
        "status": "success",
        "data": {
            "interpretation": check.interpretation,
            "interpretation_at": check.interpretation_at.isoformat()
            if check.interpretation_at
            else None,
        },
    }
