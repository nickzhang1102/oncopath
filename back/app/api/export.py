"""数据导出 API"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.api.auth import get_current_user
from app.api.deps import verify_patient_access
from app.models.user import LoginAccount
from app.models.patient import Patient
from sqlalchemy import select

router = APIRouter(prefix="/export", tags=["数据导出"])


@router.post("/medical-check/{check_id}")
@limiter.limit("10/minute")
async def export_medical_check(
    request: Request,
    check_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """导出单次检验报告 PDF"""
    from app.services.export_service import ExportService
    from app.models.medical import MedicalCheck

    # 验证归属
    result = await db.execute(
        select(MedicalCheck).join(Patient).where(
            MedicalCheck.medical_id == check_id,
            Patient.account_id == current_user.account_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="检验报告不存在")

    try:
        service = ExportService(db)
        pdf_bytes = await service.export_medical_check_pdf(check_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=check_{check_id}.pdf"
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"导出失败: {e}")
        raise HTTPException(status_code=500, detail="PDF 导出失败")


@router.post("/exam-report/{exam_id}")
@limiter.limit("10/minute")
async def export_exam_report(
    request: Request,
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """导出单次检查报告 PDF"""
    from app.services.export_service import ExportService
    from app.models.medical import MedicalExam

    result = await db.execute(
        select(MedicalExam).join(Patient).where(
            MedicalExam.exam_id == exam_id,
            Patient.account_id == current_user.account_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="检查报告不存在")

    try:
        service = ExportService(db)
        pdf_bytes = await service.export_medical_exam_pdf(exam_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=exam_{exam_id}.pdf"
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"导出失败: {e}")
        raise HTTPException(status_code=500, detail="PDF 导出失败")


@router.post("/pathology-report/{report_id}")
@limiter.limit("10/minute")
async def export_pathology_report(
    request: Request,
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """导出单次病理报告 PDF"""
    from app.services.export_service import ExportService
    from app.models.medical import PathologyReport

    result = await db.execute(
        select(PathologyReport).join(Patient).where(
            PathologyReport.report_id == report_id,
            Patient.account_id == current_user.account_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="病理报告不存在")

    try:
        service = ExportService(db)
        pdf_bytes = await service.export_pathology_report_pdf(report_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=pathology_{report_id}.pdf"
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"导出失败: {e}")
        raise HTTPException(status_code=500, detail="PDF 导出失败")


@router.post("/patient-timeline/{patient_id}")
@limiter.limit("10/minute")
async def export_patient_timeline(
    request: Request,
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """导出时间线 PDF"""
    from app.services.export_service import ExportService

    await verify_patient_access(db, patient_id, current_user.account_id)

    try:
        service = ExportService(db)
        pdf_bytes = await service.export_patient_timeline_pdf(patient_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=timeline_{patient_id}.pdf"
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"导出失败: {e}")
        raise HTTPException(status_code=500, detail="PDF 导出失败")


@router.post("/patient-summary/{patient_id}")
@limiter.limit("10/minute")
async def export_patient_summary(
    request: Request,
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """导出完整病历 PDF"""
    from app.services.export_service import ExportService

    await verify_patient_access(db, patient_id, current_user.account_id)

    try:
        service = ExportService(db)
        pdf_bytes = await service.export_patient_summary_pdf(patient_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=summary_{patient_id}.pdf"
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"导出失败: {e}")
        raise HTTPException(status_code=500, detail="PDF 导出失败")