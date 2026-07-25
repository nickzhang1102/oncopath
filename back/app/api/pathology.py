"""病理报告 API - PathologyReport CRUD + 图片管理 + AI解读"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete
from sqlalchemy.orm import selectinload
from typing import Optional, List
import base64
import logging

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.medical import PathologyReport, PathologyIHC
from app.schemas.medical import (
    PathologyReportCreate, PathologyReportResponse,
    PathologyReportQuery, PathologyReportUpdate,
)
from app.services.interpretation_service import InterpretationService
from app.services.patient_service import PatientService

router = APIRouter()
logger = logging.getLogger(__name__)


def build_pathology_response(report: PathologyReport, include_ihc: bool = True) -> PathologyReportResponse:
    """构建病理报告响应，添加 has_image 计算字段和 IHC 子记录"""
    ihc_markers = []
    if include_ihc and hasattr(report, 'ihc_markers') and report.ihc_markers:
        ihc_markers = report.ihc_markers
    return PathologyReportResponse(
        report_id=report.report_id,
        patient_id=report.patient_id,
        report_title=report.report_title,
        report_date=report.report_date,
        hospital=report.hospital,
        comment=report.comment,
        has_image=report.image_path is not None,
        created_at=report.created_at,
        diagnosis=report.diagnosis,
        cancer_type=report.cancer_type,
        stage=report.stage,
        histology_type=report.histology_type,
        immunohistochemistry=report.immunohistochemistry,
        gene_testing=report.gene_testing,
        ihc_markers=ihc_markers,
        interpretation=report.interpretation,
        interpretation_at=report.interpretation_at,
    )


@router.post("/pathology/query", response_model=List[PathologyReportResponse])
async def query_pathology_reports(
    query: PathologyReportQuery,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """查询病理报告"""
    await PatientService.verify_ownership(db, query.patient_id, current_user.account_id)

    result = await db.execute(
        select(PathologyReport).options(
            selectinload(PathologyReport.ihc_markers)
        ).where(
            PathologyReport.patient_id == query.patient_id
        )
        .order_by(desc(PathologyReport.report_date)).offset(query.offset).limit(query.limit)
    )
    reports = result.scalars().all()

    return [build_pathology_response(r) for r in reports]


@router.post("/pathology", response_model=PathologyReportResponse)
async def create_pathology_report(
    data: PathologyReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """创建病理报告"""
    await PatientService.verify_ownership(db, data.patient_id, current_user.account_id)

    # 图片大小限制：10MB (与 image_report.py 一致)
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    image_data = None
    if data.image_data:
        image_data = base64.b64decode(data.image_data)
        if len(image_data) > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=413, detail="图片大小超过10MB限制")

    report_data = {
        "patient_id": data.patient_id,
        "report_title": data.report_title,
        "report_date": data.report_date,
        "hospital": data.hospital,
        "comment": data.comment,
        "diagnosis": data.diagnosis,
        "cancer_type": data.cancer_type,
        "stage": data.stage,
        "histology_type": data.histology_type,
        "immunohistochemistry": data.immunohistochemistry,
        "gene_testing": data.gene_testing,
    }
    # 仅在有图片数据时创建记录
    report = PathologyReport(**report_data)
    db.add(report)
    await db.flush()

    # 保存图片到文件系统
    if image_data is not None:
        try:
            from app.services.storage_service import get_storage_service
            storage = get_storage_service()
            image_type = data.image_type or None
            if not image_type:
                image_type = "pdf" if image_data[:4] == b"%PDF" else "jpeg"
            ext = "jpg" if image_type == "jpeg" else (image_type or "jpg")
            image_path = await storage.save_pathology_image(report.report_id, image_data, ext)
            report.image_path = image_path
            report.image_type = image_type
        except Exception as e:
            logger.warning(f"病理图片文件存储失败: {str(e)}")

    # 创建免疫组化结构化子记录
    if data.ihc_markers:
        for marker in data.ihc_markers:
            ihc = PathologyIHC(
                report_id=report.report_id,
                marker_name=marker.marker_name,
                result=marker.result,
                intensity=marker.intensity,
                percentage=marker.percentage,
            )
            db.add(ihc)

    await db.commit()
    await db.refresh(report)
    # The response includes this relationship; load it explicitly for AsyncSession.
    await db.refresh(report, ["ihc_markers"])

    return build_pathology_response(report)


@router.get("/pathology/{report_id}", response_model=PathologyReportResponse)
async def get_pathology_report_detail(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取病理报告详情"""
    result = await db.execute(
        select(PathologyReport).options(
            selectinload(PathologyReport.ihc_markers)
        ).join(Patient).where(
            PathologyReport.report_id == report_id,
            Patient.account_id == current_user.account_id
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="记录不存在")

    return build_pathology_response(report)


@router.get("/pathology/{report_id}/image")
async def get_pathology_image(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取病理报告图片"""
    result = await db.execute(
        select(PathologyReport).join(Patient).where(
            PathologyReport.report_id == report_id,
            Patient.account_id == current_user.account_id
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    image_data = None

    # 优先从文件系统读取
    if report.image_path:
        try:
            from app.services.storage_service import get_storage_service
            storage = get_storage_service()
            ext = "jpg" if report.image_type == "jpeg" else (report.image_type or "jpg")
            image_data = await storage.read_pathology_image(report_id, ext)
        except Exception as e:
            logger.error(f"病理图片文件读取失败: {str(e)}")

    if not image_data:
        raise HTTPException(status_code=404, detail="图片不存在")

    image_type = report.image_type or ("pdf" if image_data[:4] == b"%PDF" else "jpeg")

    return {
        "image_data": base64.b64encode(image_data).decode('utf-8'),
        "image_type": image_type
    }


@router.put("/pathology/{report_id}", response_model=PathologyReportResponse)
async def update_pathology_report(
    report_id: int,
    data: PathologyReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """更新病理报告"""
    result = await db.execute(
        select(PathologyReport).join(Patient).where(
            PathologyReport.report_id == report_id,
            Patient.account_id == current_user.account_id
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="记录不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 弹出 ihc_markers（非 PathologyReport 列字段，需单独处理）
    ihc_markers_data = update_data.pop('ihc_markers', None)

    # 处理图片数据
    image_data_raw = update_data.pop('image_data', None)
    update_data.pop('image_type', None)  # image_type 从图片数据推断，不直接设置
    if 'image_data' in data.model_dump(exclude_unset=True):
        if image_data_raw is not None:
            image_bytes = base64.b64decode(image_data_raw)
            if len(image_bytes) > 10 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="图片大小超过10MB限制")

            # 同时写入文件系统
            try:
                from app.services.storage_service import get_storage_service
                storage = get_storage_service()
                image_type = data.image_type or None
                if not image_type:
                    image_type = "pdf" if image_bytes[:4] == b"%PDF" else "jpeg"
                ext = "jpg" if image_type == "jpeg" else (image_type or "jpg")
                image_path = await storage.save_pathology_image(report_id, image_bytes, ext)
                report.image_path = image_path
                report.image_type = image_type
            except Exception as e:
                logger.warning(f"病理图片文件存储失败: {str(e)}")
        else:
            # 清除图片
            report.image_path = None
            report.image_type = None
            try:
                from app.services.storage_service import get_storage_service
                storage = get_storage_service()
                # 尝试删除文件系统中的图片
                for ext in ["jpg", "jpeg", "png", "pdf"]:
                    await storage.delete_pathology_image(report_id, ext)
            except Exception:
                pass

    for field, value in update_data.items():
        setattr(report, field, value)

    # IHC 标记物全覆盖更新
    if ihc_markers_data is not None:
        # 删除旧记录（cascade 已配置，手动删除确保即时生效）
        await db.execute(
            delete(PathologyIHC).where(PathologyIHC.report_id == report_id)
        )
        # 创建新记录
        for marker in ihc_markers_data:
            db.add(PathologyIHC(
                report_id=report_id,
                marker_name=marker.get('marker_name', ''),
                result=marker.get('result'),
                intensity=marker.get('intensity'),
                percentage=marker.get('percentage'),
            ))

    await db.commit()
    await db.refresh(report)
    # 重新加载 IHC 关系以包含在响应中
    await db.refresh(report, ['ihc_markers'])
    return build_pathology_response(report)


@router.delete("/pathology/{report_id}")
async def delete_pathology_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """删除病理报告"""
    result = await db.execute(
        select(PathologyReport).join(Patient).where(
            PathologyReport.report_id == report_id,
            Patient.account_id == current_user.account_id
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 清理文件系统中的病理图片
    try:
        from app.services.storage_service import get_storage_service
        storage = get_storage_service()
        for ext in ["jpg", "jpeg", "png", "pdf"]:
            await storage.delete_pathology_image(report_id, ext)
    except Exception as e:
        logging.getLogger(__name__).warning(f"删除病理图片文件失败(可忽略): {str(e)}")

    await db.delete(report)
    await db.commit()

    return {"message": "删除成功"}


# ============= AI 解读 =============

@router.post("/pathology/{report_id}/interpret")
async def interpret_pathology_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """生成 AI 病理报告解读"""
    # 验证报告归属
    result = await db.execute(
        select(PathologyReport).join(Patient).where(
            PathologyReport.report_id == report_id,
            Patient.account_id == current_user.account_id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="病理报告不存在")

    try:
        service = InterpretationService(db)
        result = await service.interpret_pathology(report_id, current_user.account_id)
        await db.commit()
        return {"status": "success", "data": result}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"病理报告AI解读失败: {e}")
        raise HTTPException(status_code=500, detail="AI解读生成失败，请稍后重试")


@router.get("/pathology/{report_id}/interpretation")
async def get_pathology_report_interpretation(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """获取病理报告已有 AI 解读"""
    result = await db.execute(
        select(PathologyReport).join(Patient).where(
            PathologyReport.report_id == report_id,
            Patient.account_id == current_user.account_id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="病理报告不存在")

    if not report.interpretation:
        return {"status": "success", "data": None}

    return {
        "status": "success",
        "data": {
            "interpretation": report.interpretation,
            "interpretation_at": report.interpretation_at.isoformat()
            if report.interpretation_at
            else None,
        },
    }
