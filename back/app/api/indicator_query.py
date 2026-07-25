"""指标查询 API - 指标历史、异常、对比查询"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import date
from typing import Optional, List

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import LoginAccount
from app.models.medical import MedicalIndex
from app.schemas.medical import (
    IndexCompareRequest, IndexCompareResponse, IndexCompareItem,
    IndexHistoryItem,
)
from app.services.patient_service import PatientService

router = APIRouter()


@router.get("/indices/history")
async def get_index_history(
    index_id: int = Query(..., description="标准指标ID"),
    patient_id: Optional[int] = Query(None, description="患者ID（可选，不提供则查询所有）"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取指标历史数据（按index_id查询）"""
    # 如果提供了patient_id，验证权限
    if patient_id:
        await PatientService.verify_ownership(db, patient_id, current_user.account_id)

    # 查询 medical_index 的 is_edit/is_chart 元信息
    index_info_result = await db.execute(
        select(MedicalIndex).where(MedicalIndex.index_id == index_id)
    )
    index_info = index_info_result.scalar_one_or_none()

    raw_sql = text("""
        SELECT d.index_name, d.index_value, d.index_unit, d.reference_value,
               d.index_status, c.medical_date, c.hospital, c.medical_id,
               d.medical_detail_id, d.index_id
        FROM medical_check_detail d
        JOIN medical_check c ON d.medical_id = c.medical_id
        JOIN patient p ON c.patient_id = p.patient_id
        WHERE p.account_id = :account_id
        AND d.index_id = :index_id
        AND (CAST(:patient_id AS INTEGER) IS NULL OR c.patient_id = CAST(:patient_id AS INTEGER))
        AND (CAST(:start_date AS DATE) IS NULL OR c.medical_date >= CAST(:start_date AS DATE))
        AND (CAST(:end_date AS DATE) IS NULL OR c.medical_date <= CAST(:end_date AS DATE))
        ORDER BY c.medical_date DESC
        LIMIT :limit
    """)

    result = await db.execute(raw_sql, {
        'account_id': current_user.account_id,
        'patient_id': patient_id,
        'index_id': index_id,
        'start_date': start_date,
        'end_date': end_date,
        'limit': limit
    })

    rows = result.mappings().all()
    return {
        'index_info': {
            'index_id': index_id,
            'index_name': index_info.index_name if index_info else (rows[0]['index_name'] if rows else ''),
            'index_unit': index_info.index_unit if index_info else None,
            'reference_min': float(index_info.reference_min) if index_info and index_info.reference_min is not None else None,
            'reference_max': float(index_info.reference_max) if index_info and index_info.reference_max is not None else None,
            'is_edit': bool(index_info.is_edit) if index_info else True,
            'is_chart': bool(index_info.is_chart) if index_info else True,
        } if index_info or rows else None,
        'history': [{
            'index_name': row['index_name'],
            'index_value': row['index_value'],
            'index_unit': row['index_unit'],
            'reference_value': row['reference_value'],
            'index_status': row['index_status'],
            'medical_date': row['medical_date'].isoformat() if row['medical_date'] else None,
            'hospital': row['hospital'],
            'medical_id': row['medical_id'],
            'medical_detail_id': row['medical_detail_id'],
            'index_id': row['index_id']
        } for row in rows]
    }


@router.get("/patients/{patient_id}/indicators/abnormal")
async def get_abnormal_indicators(
    patient_id: int,
    limit: int = Query(50, ge=1, le=500),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取患者的异常指标列表"""
    await PatientService.verify_ownership(db, patient_id, current_user.account_id)

    # 构建SQL查询，查找异常指标（支持日期过滤）
    raw_sql = text("""
        SELECT d.index_name, d.index_value, d.index_unit, d.reference_value,
               d.index_status, c.medical_date, c.hospital, c.medical_id,
               d.medical_detail_id, d.index_id
        FROM medical_check_detail d
        JOIN medical_check c ON d.medical_id = c.medical_id
        JOIN patient p ON c.patient_id = p.patient_id
        WHERE p.patient_id = :patient_id
        AND d.index_status IN ('high', 'low', 'abnormal')
        AND (CAST(:start_date AS DATE) IS NULL OR c.medical_date >= CAST(:start_date AS DATE))
        AND (CAST(:end_date AS DATE) IS NULL OR c.medical_date <= CAST(:end_date AS DATE))
        ORDER BY c.medical_date DESC
        LIMIT :limit
    """)

    result = await db.execute(raw_sql, {
        'patient_id': patient_id,
        'limit': limit,
        'start_date': start_date,
        'end_date': end_date
    })

    rows = result.mappings().all()

    return [{
        'detail_id': row['medical_detail_id'],
        'index_name': row['index_name'],
        'index_value': row['index_value'],
        'index_unit': row['index_unit'],
        'reference_value': row['reference_value'],
        'index_status': row['index_status'],
        'medical_date': row['medical_date'].isoformat() if row['medical_date'] else None,
        'hospital': row['hospital'],
        'medical_id': row['medical_id'],
        'index_id': row['index_id']
    } for row in rows]


@router.post("/indices/compare")
async def compare_indices(
    data: IndexCompareRequest,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """批量对比多个指标的历史数据（日期对齐）"""
    # 安全校验：限制对比指标数量，防止资源耗尽攻击
    MAX_COMPARE_INDICES = 20
    if len(data.index_ids) > MAX_COMPARE_INDICES:
        raise HTTPException(
            status_code=400,
            detail=f"对比指标数量超出限制（最多 {MAX_COMPARE_INDICES} 个）"
        )
    # 校验所有 index_id 必须是正整数
    for iid in data.index_ids:
        if not isinstance(iid, int) or iid <= 0:
            raise HTTPException(status_code=400, detail="指标ID必须是正整数")

    if data.patient_id:
        await PatientService.verify_ownership(db, data.patient_id, current_user.account_id)

    index_ids = data.index_ids

    # 1. 获取所有指标的元信息
    meta_result = await db.execute(
        select(MedicalIndex).where(MedicalIndex.index_id.in_(index_ids))
    )
    meta_rows = {row.index_id: row for row in meta_result.scalars().all()}

    indexes_info = []
    for iid in index_ids:
        m = meta_rows.get(iid)
        if m:
            indexes_info.append(IndexCompareItem(
                index_id=m.index_id,
                index_name=m.index_name,
                index_unit=m.index_unit,
                reference_min=float(m.reference_min) if m.reference_min is not None else None,
                reference_max=float(m.reference_max) if m.reference_max is not None else None,
                is_chart=bool(m.is_chart) if m.is_chart is not None else True,
            ))
        else:
            indexes_info.append(IndexCompareItem(
                index_id=iid, index_name=f"未知指标({iid})", is_chart=True
            ))

    # 2. 动态构建 SQL：每个指标一个 CTE，然后 FULL OUTER JOIN 对齐日期
    ctes = []
    params = {'account_id': current_user.account_id}
    if data.patient_id:
        params['patient_id'] = data.patient_id
    if data.start_date:
        params['start_date'] = data.start_date
    if data.end_date:
        params['end_date'] = data.end_date

    for i, iid in enumerate(index_ids):
        alias = f"idx{i}"
        params[f'idx_id_{i}'] = iid
        patient_filter = "AND (CAST(:patient_id AS INTEGER) IS NULL OR c.patient_id = CAST(:patient_id AS INTEGER))" if data.patient_id else ""
        date_filter = ""
        if data.start_date:
            date_filter += " AND c.medical_date >= CAST(:start_date AS DATE)"
        if data.end_date:
            date_filter += " AND c.medical_date <= CAST(:end_date AS DATE)"

        ctes.append(f"""{alias} AS (
            SELECT c.medical_date, d.index_value
            FROM medical_check_detail d
            JOIN medical_check c ON d.medical_id = c.medical_id
            JOIN patient p ON c.patient_id = p.patient_id
            WHERE p.account_id = :account_id
              AND d.index_id = :idx_id_{i}
              {patient_filter}{date_filter}
        )""")

    # 构建 FROM + JOIN
    base_alias = "idx0"
    joins = ""
    for i in range(1, len(index_ids)):
        joins += f"\n    FULL OUTER JOIN idx{i} ON {base_alias}.medical_date = idx{i}.medical_date"

    # SELECT 中用 COALESCE 取非空日期
    date_coalesce = ", ".join(f"idx{i}.medical_date" for i in range(len(index_ids)))
    select_cols = f"COALESCE({date_coalesce}) AS check_date"
    for i, iid in enumerate(index_ids):
        select_cols += f",\n    idx{i}.index_value AS val_{i}"

    sql = text(f"""
        WITH {','.join(ctes)}
        SELECT {select_cols}
        FROM {base_alias}{joins}
        ORDER BY check_date DESC
    """)

    result = await db.execute(sql, params)
    rows = result.mappings().all()

    # 3. 格式化返回数据
    aligned_data = []
    for row in rows:
        check_date = row['check_date']
        values = {}
        for i, iid in enumerate(index_ids):
            val = row.get(f'val_{i}')
            values[str(iid)] = val
        aligned_data.append({
            'date': check_date.isoformat() if check_date else None,
            'values': values,
        })

    return IndexCompareResponse(indexes=indexes_info, aligned_data=aligned_data)