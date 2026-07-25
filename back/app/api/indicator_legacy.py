"""原版UI支持接口 API - 原版兼容的查询接口"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text
from sqlalchemy.orm import selectinload
from typing import Optional, List
import logging

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.medical import (
    MedicalIndex, MedicalCheck, MedicalCheckDetail, MedicalExam,
)
from app.schemas.medical import (
    IndexValueQuery,
)
from app.services.patient_service import PatientService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/index-values/query")
async def query_index_values(
    query: IndexValueQuery,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """查询指标值"""
    await PatientService.verify_ownership(db, query.patient_id, current_user.account_id)

    raw_sql = text("""
        SELECT d.index_name, d.index_value, d.index_unit, d.reference_value,
               c.medical_date, c.hospital
        FROM medical_check_detail d
        JOIN medical_check c ON d.medical_id = c.medical_id
        WHERE c.patient_id = :patient_id
        AND (:index_name IS NULL OR d.index_name = :index_name)
        AND (:start_date IS NULL OR c.medical_date >= :start_date)
        AND (:end_date IS NULL OR c.medical_date <= :end_date)
        ORDER BY c.medical_date DESC
        LIMIT :limit
    """)

    result = await db.execute(raw_sql, {
        'patient_id': query.patient_id,
        'index_name': query.index_name,
        'start_date': query.start_date,
        'end_date': query.end_date,
        'limit': query.limit
    })

    rows = result.mappings().all()
    return [{
        'index_name': row['index_name'],
        'index_value': row['index_value'],
        'index_unit': row['index_unit'],
        'reference_value': row['reference_value'],
        'medical_date': row['medical_date'].isoformat() if row['medical_date'] else None,
        'hospital': row['hospital']
    } for row in rows]


@router.get("/checks/latest")
async def get_latest_check_data(
    patient_id: int = Query(..., description="患者ID"),
    category: str = Query(..., description="指标分类: blood_routine, biochemistry等"),
    limit: int = Query(10, ge=1, le=100, description="返回数量限制"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取最新检验数据（按分类）"""
    await PatientService.verify_ownership(db, patient_id, current_user.account_id)

    # 通过 medical_check_detail 关联 medical_index 的 category 来查询
    # 先获取该 category 下的 index_id 列表
    index_result = await db.execute(
        select(MedicalIndex.index_id).where(
            MedicalIndex.category == category,
            MedicalIndex.is_active == True
        )
    )
    index_ids = [row[0] for row in index_result.all()]

    if not index_ids:
        return []

    # 查询包含这些指标的检验记录
    result = await db.execute(
        select(MedicalCheck).options(
            selectinload(MedicalCheck.details).selectinload(MedicalCheckDetail.standard_index)
        ).where(
            MedicalCheck.patient_id == patient_id,
            MedicalCheck.details.any(MedicalCheckDetail.index_id.in_(index_ids))
        ).order_by(desc(MedicalCheck.medical_date)).limit(limit)
    )
    checks = result.scalars().all()

    # 构建响应数据
    response_list = []
    for check in checks:
        # 构建指标列表（details 已预加载）
        indices = []
        for detail in check.details:
            # 关联的标准指标（已通过 selectinload 预加载）
            index_info = None
            if detail.standard_index:
                standard_index = detail.standard_index
                index_info = {
                    'index_id': standard_index.index_id,
                    'index_name': standard_index.index_name,
                    'index_unit': standard_index.index_unit,
                    'reference_min': float(standard_index.reference_min) if standard_index.reference_min is not None else None,
                    'reference_max': float(standard_index.reference_max) if standard_index.reference_max is not None else None,
                }

            indices.append({
                'detail_id': detail.medical_detail_id,
                'index_name': detail.index_name,
                'index_value': detail.index_value,
                'index_unit': detail.index_unit,
                'reference_value': detail.reference_value,
                'index_status': detail.index_status,
                'standard_index': index_info
            })

        response_list.append({
            'medical_id': check.medical_id,
            'medical_date': check.medical_date.isoformat() if check.medical_date else None,
            'hospital': check.hospital,
            'comment': check.comment,
            'indices': indices
        })

    return response_list


@router.get("/indices")
async def get_indices(
    patient_id: int = Query(..., description="患者ID"),
    category: str = Query(..., description="指标分类: blood_routine, biochemistry等"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取指标列表（按分类）"""
    await PatientService.verify_ownership(db, patient_id, current_user.account_id)

    # 查询标准指标库
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
        'sub_category': idx.sub_category,
        'description': idx.description,
        'is_chart': idx.is_chart
    } for idx in indices]


@router.get("/exams/latest")
async def get_latest_exam_report(
    patient_id: int = Query(..., description="患者ID"),
    exam_type: Optional[str] = Query(None, description="检查类型"),
    limit: int = Query(10, ge=1, le=100, description="返回数量限制"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取最新检查报告（CT等）"""
    await PatientService.verify_ownership(db, patient_id, current_user.account_id)

    # 构建查询
    stmt = select(MedicalExam).where(
        MedicalExam.patient_id == patient_id
    )

    if exam_type:
        stmt = stmt.where(MedicalExam.exam_type == exam_type)

    stmt = stmt.order_by(desc(MedicalExam.medical_date)).limit(limit)

    result = await db.execute(stmt)
    exams = result.scalars().all()

    return [{
        'exam_id': exam.exam_id,
        'medical_date': exam.medical_date.isoformat() if exam.medical_date else None,
        'hospital': exam.hospital,
        'exam_type': exam.exam_type,
        'exam_info': exam.exam_info,
        'exam_diag': exam.exam_diag,
        'comment': exam.comment
    } for exam in exams]


@router.get("/indicators/latest")
async def get_latest_indicators_by_category(
    patient_id: int = Query(..., description="患者ID"),
    category: str = Query(..., description="分类key: blood_routine, tumor_marker等"),
    limit: int = Query(10, ge=1, le=100, description="返回指标数量限制"),
    time_limit: int = Query(1, ge=1, le=10, description="取最近几次检验记录"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """按分类获取最新指标数据（从 medical_check + medical_check_detail 查询）

    查询逻辑:
    1. 从 medical_index 获取该分类下的指标列表（按 sort 排序，限制数量）
    2. 从 medical_check 获取该患者最近 time_limit 次检验记录
    3. 关联 medical_check_detail 获取明细数据
    """
    await PatientService.verify_ownership(db, patient_id, current_user.account_id)

    # category 兼容映射: 前端可能传 tumor_markers，数据库存的是 tumor_marker
    category_mapping = {
        'tumor_markers': 'tumor_marker',
        'blood_biochemistry': 'biochemistry',
    }
    normalized_category = category_mapping.get(category, category)

    # 分类名称映射
    category_names = {
        'blood_routine': '血常规',
        'biochemistry': '生化',
        'tumor_marker': '肿瘤标志物',
        'coagulation': '凝血',
        'urine_routine': '尿常规',
        'immune': '免疫',
        'infection': '感染',
        'hormone': '激素',
    }

    raw_sql = text("""
        SELECT d.medical_detail_id AS detail_id,
               d.index_name,
               d.index_value,
               d.index_unit,
               d.reference_value,
               d.index_status,
               d.index_id,
               c.medical_date,
               c.hospital,
               c.medical_id,
               i.reference_min,
               i.reference_max
        FROM medical_check_detail d
        JOIN (
            SELECT idx.index_id
            FROM medical_index idx
            WHERE idx.category = :category
              AND idx.is_active = TRUE
            ORDER BY idx.sort
            LIMIT :limit
        ) AS r ON d.index_id = r.index_id
        JOIN (
            SELECT DISTINCT t.medical_id, t.medical_date
            FROM medical_check t
            JOIN medical_check_detail dd ON t.medical_id = dd.medical_id
            JOIN medical_index idx ON dd.index_id = idx.index_id
            WHERE t.patient_id = :patient_id
              AND idx.category = :category
            ORDER BY t.medical_date DESC
            LIMIT :time_limit
        ) AS e ON d.medical_id = e.medical_id
        JOIN medical_check c ON d.medical_id = c.medical_id
        LEFT JOIN medical_index i ON d.index_id = i.index_id
        ORDER BY e.medical_date DESC, d.index_id
    """)

    result = await db.execute(raw_sql, {
        'patient_id': patient_id,
        'category': normalized_category,
        'limit': limit,
        'time_limit': time_limit,
    })

    rows = result.mappings().all()

    # 去重：同一指标取最新日期的数据（用于列表展示）
    seen_index_ids = set()
    indicators = []
    for row in rows:
        index_id = row['index_id']
        # 无 index_id 的记录按 index_name 去重
        dedup_key = index_id if index_id else row['index_name']
        if dedup_key in seen_index_ids:
            continue
        seen_index_ids.add(dedup_key)
        indicators.append({
            'detail_id': row['detail_id'],
            'index_name': row['index_name'],
            'index_value': row['index_value'],
            'index_unit': row['index_unit'],
            'reference_value': row['reference_value'],
            'index_status': row['index_status'],
            'index_id': row['index_id'],
            'medical_date': row['medical_date'].isoformat() if row['medical_date'] else None,
            'hospital': row['hospital'],
            'medical_id': row['medical_id'],
            'reference_min': float(row['reference_min']) if row['reference_min'] is not None else None,
            'reference_max': float(row['reference_max']) if row['reference_max'] is not None else None,
        })

    return {
        'category_key': category,
        'category_name': category_names.get(normalized_category, category),
        'indicators': indicators
    }