"""上传报告API - 上传报告并自动OCR识别和指标匹配"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional, List
import logging
import base64
import hashlib
import os
import shutil
import tempfile
import json
import asyncio
from datetime import datetime, date

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import decode_token
from app.api.auth import get_current_user
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.image_report import ImageReport, ImageCategory
from app.models.ocr_review_log import OCRReviewLog
from app.models.medical import MedicalCheck, MedicalCheckDetail, MedicalExam
from app.services.ocr.ocr_result_processor import (
    process_lab_result, process_exam_result, process_pathology_result,
    REPORT_TYPE_LAB, REPORT_TYPE_EXAM,
)
from app.services.ocr.llm_ocr_parser import REPORT_TYPE_PATHOLOGY
from app.schemas.image_report import (
    ImageReportCreate, ImageReportUpdate, ImageReportResponse,
    ImageReportDetail, ImageReportListResponse, ImageReportStats,
    ImageCategoryResponse
)
from app.schemas.ocr_review import (
    OCRReviewCreate, OCRReviewResponse, OCRReviewListResponse
)
from app.services.storage_service import get_storage_service
from app.services.patient_service import PatientService

router = APIRouter(prefix="/image_reports", tags=["上传报告"])
logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

# 后台任务引用集合（防止 GC 回收未完成的 task）
_background_tasks: set = set()


def _require_cv2():
    try:
        import cv2
        return cv2
    except ImportError as exc:
        raise RuntimeError(
            "OpenCV 依赖未安装，无法读取图片尺寸或执行 OCR 图片处理。"
        ) from exc


def _task_done_callback(task: asyncio.Task) -> None:
    """后台任务完成回调：清理引用并记录未捕获异常"""
    _background_tasks.discard(task)
    if task.exception():
        logger.error(f"后台任务异常: {task.exception()}")


async def _check_report_duplicate(
    db: AsyncSession,
    patient_id: int,
    category: str,
    content_hash: str,
    account_id: int,
) -> Optional[ImageReport]:
    """检查是否存在相同的上传报告

    去重键: patient_id + account_id + category + content_hash

    放行规则: OCR 已结束但解析出 0 指标的失败记录不视为重复，
    允许同一图片重传（LLM 输出偶发不稳定时用户可直接重传，无需手动删除）。
    仍在处理中(pending/processing)的记录仍阻塞重传，避免并发处理同一图片。
    """
    conditions = [
        ImageReport.patient_id == patient_id,
        ImageReport.account_id == account_id,
        ImageReport.category == category,
        ImageReport.content_hash == content_hash,
    ]
    result = await db.execute(select(ImageReport).where(*conditions).limit(1))
    existing = result.scalar_one_or_none()
    if existing is None:
        return None

    # OCR 已结束但 0 指标的失败记录不阻塞重传
    _TERMINAL_STATUSES = ("pending_review", "failed", "completed")
    if (
        existing.total_count == 0
        and existing.matched_count == 0
        and existing.ocr_status in _TERMINAL_STATUSES
    ):
        logger.info(
            f"去重命中失败记录(report_id={existing.report_id}, "
            f"ocr_status={existing.ocr_status}, 0指标)，放行重传"
        )
        return None
    return existing


async def _auto_interpret(report_id: int, report_type: str, user_id: int):
    """OCR完成后自动触发AI解读（best-effort，失败不影响OCR流程）"""
    from app.core.database import AsyncSessionLocal
    from app.services.interpretation_service import InterpretationService

    async with AsyncSessionLocal() as db:
        try:
            # 统一查询一次
            result = await db.execute(
                select(ImageReport).where(ImageReport.report_id == report_id)
            )
            report = result.scalar_one_or_none()
            if not report:
                return

            interp = InterpretationService(db)

            if report_type == REPORT_TYPE_LAB and report.related_check_id:
                await interp.interpret_check(report.related_check_id, user_id)
            elif report_type == REPORT_TYPE_EXAM and report.related_exam_id:
                await interp.interpret_exam(report.related_exam_id, user_id)
            elif report_type == REPORT_TYPE_PATHOLOGY and report.related_pathology_id:
                await interp.interpret_pathology(report.related_pathology_id, user_id)
            else:
                return

            await db.commit()
            logger.info(f"自动解读完成: 报告ID={report_id}, 类型={report_type}")

        except ValueError as e:
            # 业务限制或数据校验失败，跳过解读不影响 OCR 结果
            logger.info(f"自动解读跳过: 报告ID={report_id}, 原因={e}")
        except Exception as e:
            logger.warning(f"自动解读失败（不影响OCR结果）: 报告ID={report_id}, 错误={e}")


def _decode_image_data(image_data_b64: str, image_type: str = "jpeg") -> tuple[bytes, int, str]:
    """解码 base64 图片/PDF数据，返回 (image_data, image_size, content_hash)

    Args:
        image_data_b64: Base64编码的数据
        image_type: 文件类型 jpeg/png/pdf

    Raises:
        HTTPException: 文件格式错误或超过大小限制(图片10MB/PDF 20MB)
    """
    max_size = 20 * 1024 * 1024 if image_type == "pdf" else 10 * 1024 * 1024
    size_label = "20MB" if image_type == "pdf" else "10MB"
    try:
        if ',' in image_data_b64:
            image_data_b64 = image_data_b64.split(',')[1]
        image_data = base64.b64decode(image_data_b64)
        image_size = len(image_data)
        if image_size > max_size:
            raise HTTPException(status_code=400, detail=f"文件大小不能超过{size_label}")
        content_hash = hashlib.sha256(image_data).hexdigest()
        return image_data, image_size, content_hash
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件数据格式错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail="文件数据格式错误")


async def _save_report_and_files(
    db: AsyncSession,
    image_report: ImageReport,
    image_data: bytes,
    image_type: Optional[str],
) -> None:
    """保存图片/PDF文件和缩略图，更新报告路径字段"""
    try:
        storage = get_storage_service()

        if image_type == 'pdf':
            # PDF: 保存原始PDF + 提取第一页为缩略图
            pdf_path = await storage.save_image(image_report.report_id, image_data, "pdf")
            image_report.image_path = pdf_path

            # 从临时文件提取第一页作为缩略图
            first_page_image = None
            if image_data:
                temp_pdf_path = None
                try:
                    temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                    temp_pdf.write(image_data)
                    temp_pdf.close()
                    temp_pdf_path = temp_pdf.name
                    from app.services.ocr.paddle_ocr_service import paddle_ocr_service
                    first_page_image = await paddle_ocr_service.extract_first_page_as_image(temp_pdf_path)
                except Exception as e:
                    logger.warning(f"PDF缩略图提取失败: {str(e)}")
                finally:
                    if temp_pdf_path:
                        try:
                            os.unlink(temp_pdf_path)
                        except OSError:
                            pass

            if first_page_image:
                try:
                    from app.utils.thumbnail import generate_thumbnail
                    thumb_data = generate_thumbnail(first_page_image)
                    thumb_path = await storage.save_thumbnail(image_report.report_id, thumb_data, "jpg")
                    image_report.thumbnail_path = thumb_path
                except Exception as te:
                    logger.warning(f"PDF缩略图生成失败: {str(te)}")
        else:
            # 图片：原有逻辑
            ext = "jpg" if image_type == "jpeg" else (image_type or "jpg")
            image_path = await storage.save_image(image_report.report_id, image_data, ext)
            image_report.image_path = image_path

            try:
                from app.utils.thumbnail import generate_thumbnail
                thumb_data = generate_thumbnail(image_data)
                thumb_path = await storage.save_thumbnail(image_report.report_id, thumb_data, "jpg")
                image_report.thumbnail_path = thumb_path
            except Exception as te:
                logger.warning(f"缩略图生成失败: {str(te)}")

        # 注意：不在内部 commit，由调用方统一管理事务边界
    except Exception as e:
        logger.warning(f"文件存储失败: {str(e)}")




@router.get("/categories", response_model=List[ImageCategoryResponse])
async def get_image_categories(
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """
    获取图片分类列表

    返回所有可用的上传报告分类。
    """
    result = await db.execute(
        select(ImageCategory)
        .where(ImageCategory.is_active == True)
        .order_by(ImageCategory.sort_order)
    )
    categories = result.scalars().all()

    return [ImageCategoryResponse.model_validate(cat) for cat in categories]


@router.post("/check-duplicate")
async def check_duplicate(
    patient_id: int = Query(..., description="患者ID"),
    category: str = Query(..., description="分类key"),
    content_hash: str = Query(..., description="文件内容SHA-256哈希"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """检查是否已存在相同的上传报告"""
    existing = await _check_report_duplicate(
        db, patient_id, category, content_hash, current_user.account_id
    )
    if existing:
        return {
            "is_duplicate": True,
            "existing_report_id": existing.report_id,
            "existing_report_title": existing.title,
        }
    return {"is_duplicate": False}


@router.post("", response_model=ImageReportResponse)
@limiter.limit("10/minute")
async def upload_image_report(
    report_data: ImageReportCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """
    上传上传报告

    上传base64编码的上传报告，系统会自动进行：
    1. PaddleOCR识别图片文本
    2. LLM智能解析表格结构，提取指标
    3. LLM匹配标准指标库（medical_index）
    4. 结果保存到medical_check_detail

    Args:
        report_data: 报告数据（含base64图片）
        background_tasks: 后台任务管理器
        db: 数据库会话
        current_user: 当前用户

    Returns:
        创建的上传报告信息
    """
    try:
        # 1. 验证患者归属
        await PatientService.get_with_ownership(db, report_data.patient_id, current_user.account_id)

        # 2. 处理图片数据
        image_data, image_size, content_hash = _decode_image_data(report_data.image_data, report_data.image_type)

        # 2.5 去重校验
        existing = await _check_report_duplicate(
            db, report_data.patient_id, report_data.category,
            content_hash, current_user.account_id,
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"该报告已上传: {existing.title}",
            )

        # 3. 创建上传报告记录
        image_report = ImageReport(
            patient_id=report_data.patient_id,
            account_id=current_user.account_id,
            title=report_data.title,
            description=report_data.description,
            category=report_data.category,
            hospital=report_data.hospital,
            department=report_data.department,
            image_type=report_data.image_type,
            image_size=image_size,
            content_hash=content_hash,
            capture_date=report_data.capture_date,
            tags=','.join(report_data.tags) if report_data.tags else None,
            notes=report_data.notes,
            is_private=report_data.is_private,
            is_important=report_data.is_important,
            ocr_status="pending"
        )

        db.add(image_report)
        await db.commit()
        await db.refresh(image_report)

        # 3.5 保存图片文件和缩略图
        await _save_report_and_files(db, image_report, image_data, report_data.image_type)
        await db.commit()  # 持久化 image_path / thumbnail_path

        logger.info(f"用户 {current_user.username} 上传了上传报告: {image_report.title}")

        # 4. 触发后台OCR处理任务
        background_tasks.add_task(
            process_ocr_task,
            image_report.report_id
        )

        return ImageReportResponse.model_validate(image_report)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传上传报告失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="上传失败")


async def process_ocr_task(report_id: int):
    """
    后台任务：处理OCR识别和报告解析

    根据分类选择不同的处理流程：
    - 检验类：OCR → LLM解析 → 匹配标准库 → 插入 medical_check + medical_check_detail
    - 检查类：OCR → LLM提取医学信息 → 插入 medical_exam
    - 病理类：OCR → LLM提取病理信息 → 插入 pathology_report
    """
    from app.core.database import AsyncSessionLocal
    from app.services.ocr.ocr_integration_service import ocr_integration_service
    from app.services.ocr.paddle_ocr_service import paddle_ocr_service
    from app.services.ocr.image_processor import image_processor

    async with AsyncSessionLocal() as db:
        try:
            # 获取报告
            result = await db.execute(
                select(ImageReport).where(ImageReport.report_id == report_id)
            )
            image_report = result.scalar_one_or_none()
            if not image_report:
                logger.error(f"报告不存在: {report_id}")
                return

            # 更新状态为处理中
            image_report.ocr_status = "processing"
            await db.commit()

            # 保存临时文件
            temp_dir = tempfile.mkdtemp()
            ext = image_report.image_type or 'jpg'
            if ext == 'pdf':
                temp_file_path = os.path.join(temp_dir, f"report_{report_id}.pdf")
            else:
                temp_file_path = os.path.join(temp_dir, f"report_{report_id}.{ext}")

            with open(temp_file_path, 'wb') as f:
                # 从文件系统读取
                img_bytes = None
                if image_report.image_path:
                    try:
                        storage = get_storage_service()
                        _ext = "jpg" if image_report.image_type == "jpeg" else (image_report.image_type or "jpg")
                        img_bytes = await storage.read_image(report_id, _ext)
                    except Exception as e:
                        logger.error(f"文件系统读取失败: {str(e)}")
                if img_bytes is None:
                    image_report.ocr_status = "failed"
                    image_report.ocr_error = "图片数据不存在"
                    await db.commit()
                    return
                f.write(img_bytes)

            # PDF: 校验 + 获取页数
            if image_report.image_type == 'pdf':
                is_valid, error_msg = image_processor.validate_pdf(temp_file_path)
                if not is_valid:
                    image_report.ocr_status = "failed"
                    image_report.ocr_error = error_msg
                    await db.commit()
                    return
                page_count = await paddle_ocr_service.get_page_count(temp_file_path)
                image_report.page_count = page_count

            logger.info(f"开始OCR处理: 报告ID={report_id}, 分类={image_report.category}, 类型={image_report.image_type}")

            # 调用OCR集成服务（自动根据分类选择处理流程）
            ocr_result = await ocr_integration_service.process_medical_report_image(
                temp_file_path,
                category=image_report.category,
                is_pdf=(image_report.image_type == 'pdf'),
                db=db
            )

            # 获取报告类型
            report_type = ocr_result.get('report_type', REPORT_TYPE_LAB)
            raw_text = ocr_result.get('raw_text', '')
            llm_raw_response = ocr_result.get('llm_raw_response', '')

            # 更新报告基本信息
            image_report.ocr_text = raw_text
            image_report.ocr_status = "pending_review"
            image_report.llm_raw_response = llm_raw_response
            image_report.report_type = report_type

            # 根据报告类型进行不同的处理
            if report_type == REPORT_TYPE_LAB:
                _lab_id, _skipped = await process_lab_result(db, image_report, ocr_result)
            elif report_type == REPORT_TYPE_EXAM:
                await process_exam_result(db, image_report, ocr_result)
            else:
                await process_pathology_result(db, image_report, ocr_result)

            await db.commit()

            # 自动触发AI解读（best-effort，失败不影响OCR结果）
            if image_report.account_id:
                task = asyncio.create_task(_auto_interpret(report_id, report_type, image_report.account_id))
                _background_tasks.add(task)
                task.add_done_callback(_task_done_callback)

            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            shutil.rmtree(temp_dir, ignore_errors=True)

            logger.info(f"OCR处理完成: 报告ID={report_id}, 类型={report_type}")

        except Exception as e:
            logger.error(f"OCR处理失败: 报告ID={report_id}, 错误={str(e)}", exc_info=True)

            # 更新状态为失败
            try:
                result = await db.execute(
                    select(ImageReport).where(ImageReport.report_id == report_id)
                )
                image_report = result.scalar_one_or_none()
                if image_report:
                    image_report.ocr_status = "failed"
                    image_report.ocr_error = str(e)
                    await db.commit()
            except Exception as update_error:
                logger.error(f"更新OCR状态失败: {str(update_error)}")



@router.get("", response_model=ImageReportListResponse)
async def get_image_reports(
    patient_id: Optional[int] = Query(None, description="患者ID"),
    category: Optional[str] = Query(None, description="分类"),
    hospital: Optional[str] = Query(None, description="医院"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    ocr_status: Optional[str] = Query(None, description="OCR状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """
    获取上传报告列表

    支持按患者、分类、医院、日期范围筛选和搜索。
    """
    try:
        # 构建查询
        query = select(ImageReport).where(
            ImageReport.account_id == current_user.account_id
        )

        # 应用筛选条件
        if patient_id:
            query = query.where(ImageReport.patient_id == patient_id)

        if category:
            query = query.where(ImageReport.category == category)

        if hospital:
            hospital_escaped = hospital.replace('%', r'\%').replace('_', r'\_')
            query = query.where(ImageReport.hospital.ilike(f"%{hospital_escaped}%", escape='\\'))

        if start_date:
            query = query.where(ImageReport.capture_date >= start_date)

        if end_date:
            query = query.where(ImageReport.capture_date <= end_date)

        if search:
            search_escaped = search.replace('%', r'\%').replace('_', r'\_')
            search_filter = f"%{search_escaped}%"
            query = query.where(
                or_(
                    ImageReport.title.ilike(search_filter, escape='\\'),
                    ImageReport.description.ilike(search_filter, escape='\\'),
                    ImageReport.notes.ilike(search_filter, escape='\\'),
                    ImageReport.ocr_text.ilike(search_filter, escape='\\')
                )
            )

        if ocr_status:
            query = query.where(ImageReport.ocr_status == ocr_status)

        # 统计总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # 分页
        query = query.order_by(ImageReport.upload_date.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await db.execute(query)
        reports = result.scalars().all()

        # 获取医院列表用于筛选
        hospital_query = select(ImageReport.hospital).where(
            ImageReport.account_id == current_user.account_id,
            ImageReport.hospital.isnot(None)
        ).distinct()
        hospital_result = await db.execute(hospital_query)
        hospitals = [h[0] for h in hospital_result.all() if h[0]]

        # 批量预加载分类名称（解决 N+1 查询）
        category_keys = {r.category for r in reports if r.category}
        category_map = {}
        if category_keys:
            cat_result = await db.execute(
                select(ImageCategory.category_key, ImageCategory.category_name)
                .where(ImageCategory.category_key.in_(category_keys))
            )
            category_map = dict(cat_result.all())

        # 为报告添加分类中文名称
        reports_with_name = []
        for report in reports:
            report_dict = report.to_dict()
            report_dict['category_name'] = category_map.get(report.category, report.category)
            reports_with_name.append(ImageReportResponse.model_validate(report_dict))

        return ImageReportListResponse(
            items=reports_with_name,
            total=total,
            pages=(total + per_page - 1) // per_page,
            current_page=page,
            per_page=per_page,
            hospitals=hospitals
        )

    except Exception as e:
        logger.error(f"获取上传报告列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取报告列表失败")


@router.get("/stats", response_model=ImageReportStats)
async def get_image_stats(
    patient_id: Optional[int] = Query(None, description="患者ID"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """
    获取上传报告统计信息

    包括总数、分类统计、医院统计和最近报告。
    """
    try:
        # 构建基础查询
        base_filter = [ImageReport.account_id == current_user.account_id]
        if patient_id:
            base_filter.append(ImageReport.patient_id == patient_id)

        # 总数统计
        count_query = select(func.count()).select_from(ImageReport).where(*base_filter)
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()

        # 按分类统计（关联 image_category 表获取中文名称）
        category_query = select(
            ImageReport.category,
            func.count(ImageReport.report_id).label('count'),
            ImageCategory.category_name
        ).outerjoin(
            ImageCategory, ImageReport.category == ImageCategory.category_key
        ).where(*base_filter).group_by(ImageReport.category, ImageCategory.category_name)

        category_result = await db.execute(category_query)
        category_stats = [
            {
                'category': row[0],
                'category_name': row[2] or row[0],  # 如果没有中文名则使用key
                'count': row[1]
            }
            for row in category_result.all()
        ]

        # 按医院统计
        hospital_query = select(
            ImageReport.hospital,
            func.count(ImageReport.report_id).label('count')
        ).where(
            *base_filter,
            ImageReport.hospital.isnot(None)
        ).group_by(ImageReport.hospital)

        hospital_result = await db.execute(hospital_query)
        hospital_stats = [
            {'hospital': row[0], 'count': row[1]}
            for row in hospital_result.all()
        ]

        # 最近上传的报告
        recent_query = select(ImageReport).where(*base_filter).order_by(
            ImageReport.upload_date.desc()
        ).limit(5)

        recent_result = await db.execute(recent_query)
        recent_reports = recent_result.scalars().all()

        # 批量预加载分类名称（解决 N+1 查询）
        recent_category_keys = {r.category for r in recent_reports if r.category}
        recent_category_map = {}
        if recent_category_keys:
            cat_result = await db.execute(
                select(ImageCategory.category_key, ImageCategory.category_name)
                .where(ImageCategory.category_key.in_(recent_category_keys))
            )
            recent_category_map = dict(cat_result.all())

        # 为最近报告添加分类中文名称
        recent_reports_with_name = []
        for report in recent_reports:
            report_dict = report.to_dict()
            report_dict['category_name'] = recent_category_map.get(report.category, report.category)
            recent_reports_with_name.append(ImageReportResponse.model_validate(report_dict))

        return ImageReportStats(
            total_count=total_count,
            category_stats=category_stats,
            hospital_stats=hospital_stats,
            recent_reports=recent_reports_with_name
        )

    except Exception as e:
        logger.error(f"获取上传报告统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取报告统计失败")


async def _validate_and_prepare_image(
    image_data: bytes, image_type: str, report_id: int
) -> tuple[str, str, bool]:
    """创建临时文件并验证图片/PDF，返回 (temp_file_path, temp_dir, is_pdf)"""
    from app.services.ocr.paddle_ocr_service import paddle_ocr_service
    from app.services.ocr.image_processor import image_processor

    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"report_{report_id}.{image_type or 'jpg'}")

    with open(temp_file_path, 'wb') as f:
        f.write(image_data)

    is_pdf = image_type == 'pdf'
    if is_pdf:
        is_valid, error_msg = image_processor.validate_pdf(temp_file_path)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f'PDF验证失败: {error_msg}')
    else:
        is_valid, error_msg = image_processor.validate_image(temp_file_path)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f'图片验证失败: {error_msg}')

    return temp_file_path, temp_dir, is_pdf


async def _run_ocr_pipeline(
    temp_file_path: str, is_pdf: bool, category: str, db: AsyncSession
) -> dict:
    """执行 OCR 识别管线：基础 OCR → 可选表格识别 → 合并文本。

    返回 dict: rec_texts, raw_text, ocr_line_count, metadata, use_table_rec, report_type
    """
    from app.services.ocr.paddle_ocr_service import paddle_ocr_service
    from app.services.ocr.llm_ocr_parser import get_report_type
    from app.services.ocr.ocr_config import ocr_config
    from app.services.ocr.ocr_integration_service import group_texts_by_row

    report_type = await get_report_type(category, db=db) if category else REPORT_TYPE_LAB
    rec_texts = None
    use_table_rec = False

    # 基础 OCR
    try:
        ocr_results = await asyncio.wait_for(
            paddle_ocr_service.extract_text_from_image(temp_file_path),
            timeout=300
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail='OCR识别超时，请尝试上传更小的图片')

    # 记录图片尺寸
    try:
        cv2 = _require_cv2()
        img = cv2.imread(temp_file_path)
        if img is not None:
            h, w = img.shape[:2]
            logger.info(f"[OCR流程] 图片尺寸: {w}x{h}, OCR识别条目数: {len(ocr_results)}")
    except Exception:
        pass

    ocr_row_texts = group_texts_by_row(ocr_results)

    # 检验类额外走表格识别
    if report_type == REPORT_TYPE_LAB and ocr_config.use_table_recognition:
        try:
            table_result = await asyncio.wait_for(
                paddle_ocr_service.extract_table_from_image(temp_file_path),
                timeout=300
            )
            if table_result.get('success'):
                table_texts = table_result['rec_texts']
                use_table_rec = True
                rec_texts = list(table_texts) + ['===== 基础OCR补充 ====='] + list(ocr_row_texts)
                logger.info(f"[表格识别] 拼接后行数={len(rec_texts)} (表格={len(table_texts)}, OCR={len(ocr_row_texts)})")
            else:
                logger.warning(f"[表格识别] 失败({table_result.get('error')})，使用基础OCR")
        except asyncio.TimeoutError:
            logger.warning("[表格识别] 超时，使用基础OCR")
        except Exception as e:
            logger.warning(f"[表格识别] 异常({e})，使用基础OCR", exc_info=True)

    if rec_texts is None:
        rec_texts = ocr_row_texts

    raw_text = "\n".join(rec_texts)
    metadata = await paddle_ocr_service._extract_metadata(ocr_results)

    return {
        'rec_texts': rec_texts,
        'raw_text': raw_text,
        'ocr_line_count': len(rec_texts),
        'metadata': metadata,
        'use_table_rec': use_table_rec,
        'report_type': report_type,
    }


async def _parse_by_report_type(
    report_type: str, rec_texts: list, category: str,
    raw_text: str, metadata: dict, use_table_rec: bool,
    db: AsyncSession,
) -> dict:
    """按报告类型调用 LLM 解析，返回 ocr_result dict。"""
    from app.services.ocr.llm_ocr_parser import llm_ocr_parser

    if report_type == REPORT_TYPE_LAB:
        standard_indicators = await llm_ocr_parser._get_standard_indicators(category)
        parse_result = await llm_ocr_parser.parse_with_matching(rec_texts, category)

        if isinstance(parse_result, dict):
            indicators = parse_result.get('indicators', [])
            llm_raw_response = parse_result.get('llm_raw_response', '')
        else:
            indicators = parse_result
            llm_raw_response = ''

        matched_count = sum(1 for ind in indicators if ind.get('matched_index_id'))

        return {
            'report_type': REPORT_TYPE_LAB,
            'indicators': indicators,
            'matched_count': matched_count,
            'total_count': len(indicators),
            'metadata': metadata,
            'raw_text': raw_text,
            'parse_method': 'table_recognition' if use_table_rec else 'llm',
            'llm_raw_response': llm_raw_response,
        }

    elif report_type == REPORT_TYPE_EXAM:
        exam_info = await llm_ocr_parser.parse_exam_report(rec_texts, category)
        return {
            'report_type': REPORT_TYPE_EXAM,
            'exam_info': exam_info,
            'metadata': metadata,
            'raw_text': raw_text,
            'parse_method': 'llm',
            'llm_raw_response': exam_info.get('llm_raw_response', ''),
        }

    else:
        pathology_info = await llm_ocr_parser.parse_pathology_report(rec_texts, category)
        return {
            'report_type': REPORT_TYPE_PATHOLOGY,
            'pathology_info': pathology_info,
            'metadata': metadata,
            'raw_text': raw_text,
            'parse_method': 'llm',
            'llm_raw_response': pathology_info.get('llm_raw_response', ''),
        }


async def _process_and_save_result(
    db: AsyncSession, image_report: ImageReport,
    ocr_result: dict, report_type: str,
) -> dict:
    """根据报告类型保存 OCR 结果，返回完成事件的 data 部分。"""
    medical_id = None
    lab_skipped = 0
    exam_id = None
    pathology_id = None

    if report_type == REPORT_TYPE_LAB:
        medical_id, lab_skipped = await process_lab_result(db, image_report, ocr_result)
    elif report_type == REPORT_TYPE_EXAM:
        exam_id = await process_exam_result(db, image_report, ocr_result)
    else:
        pathology_id = await process_pathology_result(db, image_report, ocr_result)

    await db.commit()

    total_count = ocr_result.get('total_count', 0)
    matched_count = ocr_result.get('matched_count', 0)

    if report_type == REPORT_TYPE_LAB:
        skip_msg = f'，跳过重复{lab_skipped}个' if lab_skipped else ''
        message = f'处理完成！识别{total_count}个指标，匹配成功{matched_count}个{skip_msg}'
    elif report_type == REPORT_TYPE_EXAM:
        message = '处理完成！已提取检查信息并创建检查记录'
    else:
        message = '处理完成！已提取病理信息并创建病理记录'

    return {
        'status': 'completed',
        'message': message,
        'data': {
            'report_id': image_report.report_id,
            'title': image_report.title,
            'ocr_status': image_report.ocr_status,
            'report_type': report_type,
            'total_count': total_count if report_type == REPORT_TYPE_LAB else 0,
            'matched_count': matched_count if report_type == REPORT_TYPE_LAB else 0,
            'medical_id': medical_id,
            'exam_id': exam_id,
            'pathology_id': pathology_id,
        },
    }


@router.post("/upload-stream")
@limiter.limit("10/minute")
async def upload_image_report_stream(
    report_data: ImageReportCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """
    上传上传报告（SSE流式响应，实时返回处理进度）

    返回SSE事件流，包含：
    - status: 当前处理状态
    - message: 进度消息
    - data: 处理结果（完成时返回）
    """

    async def generate_progress():
        temp_file_path = None
        temp_dir = None
        try:
            # 发送开始事件
            yield f"data: {json.dumps({'status': 'init', 'message': '正在验证数据...'})}\n\n"
            await asyncio.sleep(0.1)

            # 0. 解码图片 + 去重校验
            try:
                image_data, image_size, content_hash = _decode_image_data(report_data.image_data, report_data.image_type)
            except HTTPException as e:
                yield f"data: {json.dumps({'status': 'error', 'message': e.detail})}\n\n"
                return

            existing = await _check_report_duplicate(
                db, report_data.patient_id, report_data.category,
                content_hash, current_user.account_id,
            )
            if existing:
                yield f"data: {json.dumps({'status': 'error', 'message': f'该报告已上传: {existing.title}', 'error_code': 'duplicate'})}\n\n"
                return

            # 1. 验证患者归属
            try:
                await PatientService.get_with_ownership(db, report_data.patient_id, current_user.account_id)
            except HTTPException as e:
                yield f"data: {json.dumps({'status': 'error', 'message': e.detail})}\n\n"
                return

            yield f"data: {json.dumps({'status': 'processing', 'message': '正在处理图片数据...'})}\n\n"
            await asyncio.sleep(0.1)

            # 2. 创建报告记录
            image_report = ImageReport(
                patient_id=report_data.patient_id,
                account_id=current_user.account_id,
                title=report_data.title,
                description=report_data.description,
                category=report_data.category,
                hospital=report_data.hospital,
                department=report_data.department,
                image_type=report_data.image_type,
                image_size=image_size,
                content_hash=content_hash,
                capture_date=report_data.capture_date,
                tags=','.join(report_data.tags) if report_data.tags else None,
                notes=report_data.notes,
                is_private=report_data.is_private,
                is_important=report_data.is_important,
                ocr_status="processing"
            )
            db.add(image_report)
            await db.commit()
            await db.refresh(image_report)

            await _save_report_and_files(db, image_report, image_data, image_report.image_type)
            await db.commit()  # 持久化 image_path / thumbnail_path

            yield f"data: {json.dumps({'status': 'creating', 'message': '正在创建报告记录...'})}\n\n"
            await asyncio.sleep(0.1)

            # 3. 验证图片 + 创建临时文件
            yield f"data: {json.dumps({'status': 'ocr', 'message': '正在初始化OCR引擎...'})}\n\n"
            await asyncio.sleep(0.1)

            try:
                temp_file_path, temp_dir, is_pdf = await _validate_and_prepare_image(
                    image_data, image_report.image_type, image_report.report_id
                )
            except HTTPException as e:
                yield f"data: {json.dumps({'status': 'error', 'message': e.detail})}\n\n"
                return

            if is_pdf:
                from app.services.ocr.paddle_ocr_service import paddle_ocr_service
                page_count = await paddle_ocr_service.get_page_count(temp_file_path)
                image_report.page_count = page_count

            # 4. OCR 识别
            yield f"data: {json.dumps({'status': 'recognizing', 'message': '正在进行OCR识别...'})}\n\n"
            try:
                ocr_info = await _run_ocr_pipeline(temp_file_path, is_pdf, image_report.category, db)
            except HTTPException as e:
                image_report.ocr_status = "failed"
                await db.commit()
                yield f"data: {json.dumps({'status': 'error', 'message': e.detail})}\n\n"
                return

            report_type = ocr_info['report_type']
            rec_texts = ocr_info['rec_texts']
            raw_text = ocr_info['raw_text']

            line_count = ocr_info['ocr_line_count']
            yield f"data: {json.dumps({'status': 'recognized', 'message': f'OCR识别完成，识别到{line_count}行文本'})}\n\n"

            # 5. LLM 解析
            if report_type == REPORT_TYPE_LAB:
                yield f"data: {json.dumps({'status': 'parsing', 'message': '正在AI解析检验指标...'})}\n\n"
            elif report_type == REPORT_TYPE_EXAM:
                yield f"data: {json.dumps({'status': 'parsing', 'message': '正在AI提取检查信息...'})}\n\n"
            else:
                yield f"data: {json.dumps({'status': 'parsing', 'message': '正在AI提取病理信息...'})}\n\n"

            ocr_result = await _parse_by_report_type(
                report_type, rec_texts, image_report.category,
                raw_text, ocr_info['metadata'], ocr_info['use_table_rec'], db,
            )

            if report_type == REPORT_TYPE_LAB:
                parsed_msg = f'解析完成：{ocr_result.get("total_count", 0)}个指标，匹配{ocr_result.get("matched_count", 0)}个'
            elif report_type == REPORT_TYPE_EXAM:
                parsed_msg = '检查信息提取完成'
            elif report_type == REPORT_TYPE_PATHOLOGY:
                parsed_msg = '病理信息提取完成'
            else:
                parsed_msg = '解析完成'
            yield f"data: {json.dumps({'status': 'parsed', 'message': parsed_msg})}\n\n"

            # 6. 保存结果
            image_report.ocr_text = raw_text
            image_report.ocr_status = "pending_review"
            image_report.llm_raw_response = ocr_result.get('llm_raw_response', '')
            image_report.report_type = report_type

            yield f"data: {json.dumps({'status': 'saving', 'message': '正在保存数据...'})}\n\n"
            await asyncio.sleep(0.1)

            result_data = await _process_and_save_result(db, image_report, ocr_result, report_type)

            # 自动触发AI解读
            if image_report.account_id:
                task = asyncio.create_task(_auto_interpret(image_report.report_id, report_type, image_report.account_id))
                _background_tasks.add(task)
                task.add_done_callback(_task_done_callback)

            # 清理临时文件
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

            yield f"data: {json.dumps(result_data)}\n\n"

        except Exception as e:
            logger.error(f"SSE上传处理失败: {str(e)}", exc_info=True)
            # 确保异常路径也将 ocr_status 标记为 failed
            try:
                if 'image_report' in locals() and image_report.ocr_status == "processing":
                    image_report.ocr_status = "failed"
                    await db.commit()
            except Exception:
                pass
            yield f"data: {json.dumps({'status': 'error', 'message': '处理失败'})}\n\n"
        finally:
            # 异常路径兜底清理
            try:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/{report_id}", response_model=ImageReportDetail)
async def get_image_report_detail(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """
    获取上传报告详情

    包含完整的报告信息和图片数据。
    """
    try:
        result = await db.execute(
            select(ImageReport).where(
                ImageReport.report_id == report_id,
                ImageReport.account_id == current_user.account_id
            )
        )
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        report_dict = report.to_dict(include_image=True)

        return ImageReportDetail(**report_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取上传报告详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取报告详情失败")


@router.put("/{report_id}", response_model=ImageReportResponse)
async def update_image_report(
    report_id: int,
    update_data: ImageReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """
    更新上传报告

    更新报告的基本信息（不包括图片）。
    """
    try:
        result = await db.execute(
            select(ImageReport).where(
                ImageReport.report_id == report_id,
                ImageReport.account_id == current_user.account_id
            )
        )
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        # 更新字段
        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            if field == 'tags' and isinstance(value, list):
                value = ','.join(value)
            setattr(report, field, value)

        await db.commit()
        await db.refresh(report)

        logger.info(f"用户 {current_user.username} 更新了上传报告: {report.title}")

        return ImageReportResponse.model_validate(report)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新上传报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新报告失败")


@router.delete("/{report_id}")
async def delete_image_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """
    删除上传报告

    删除指定的上传报告及其关联数据。
    """
    try:
        result = await db.execute(
            select(ImageReport).where(
                ImageReport.report_id == report_id,
                ImageReport.account_id == current_user.account_id
            )
        )
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        report_title = report.title

        # 清理文件系统中的图片和缩略图
        try:
            storage = get_storage_service()
            for ext in ["jpg", "jpeg", "png", "pdf"]:
                await storage.delete_image(report_id, ext)
            await storage.delete_thumbnail(report_id)
        except Exception as e:
            logger.warning(f"删除报告文件失败(可忽略): {str(e)}")

        await db.delete(report)
        await db.commit()

        logger.info(f"用户 {current_user.username} 删除了上传报告: {report_title}")

        return {"status": "success", "message": "报告删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除上传报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除报告失败")


@router.get("/{report_id}/image")
async def get_image_data(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """
    获取图片数据

    从文件系统读取图片文件。
    """
    try:
        result = await db.execute(
            select(ImageReport).where(
                ImageReport.report_id == report_id,
                ImageReport.account_id == current_user.account_id
            )
        )
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        image_data = None

        # 从文件系统读取
        if report.image_path:
            try:
                storage = get_storage_service()
                ext = "jpg" if report.image_type == "jpeg" else (report.image_type or "jpg")
                image_data = await storage.read_image(report_id, ext)
            except Exception as e:
                logger.error(f"文件系统读取失败: {str(e)}")

        if not image_data:
            raise HTTPException(status_code=404, detail="图片数据不存在")

        # 返回base64编码的文件
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        if report.image_type == 'pdf':
            mime_type = 'application/pdf'
        else:
            mime_type = f'image/{report.image_type or "jpeg"}'
        image_data_url = f"data:{mime_type};base64,{image_base64}"

        return {
            "status": "success",
            "data": {
                "image_data": image_data_url,
                "image_type": report.image_type,
                "image_size": report.image_size
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取图片数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取图片数据失败")


@router.get("/{report_id}/thumbnail")
async def get_thumbnail(
    report_id: int,
    token: Optional[str] = Query(None, description="访问令牌(用于img标签)"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """获取缩略图，直接返回JPEG二进制数据

    支持两种认证方式: Authorization header 或 token query param
    """
    from fastapi.responses import Response

    # 认证：优先 header，回退 query param
    access_token = None
    if credentials:
        access_token = credentials.credentials
    elif token:
        access_token = token

    if not access_token:
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    payload = decode_token(access_token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="无效的访问令牌")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="令牌缺少用户标识")
    try:
        account_id = int(sub)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="令牌用户标识无效")

    try:
        result = await db.execute(
            select(ImageReport).where(
                ImageReport.report_id == report_id,
                ImageReport.account_id == account_id
            )
        )
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        thumb_data = None

        # 优先从文件系统读取缩略图
        if report.thumbnail_path:
            try:
                storage = get_storage_service()
                thumb_data = await storage.read_thumbnail(report_id)
            except Exception as e:
                logger.warning(f"缩略图文件读取失败: {str(e)}")

        # 回退：从文件系统读取原图并动态生成缩略图
        if thumb_data is None and report.image_path:
            try:
                storage = get_storage_service()
                ext = "jpg" if report.image_type == "jpeg" else (report.image_type or "jpg")
                image_data = await storage.read_image(report_id, ext)
                if image_data:
                    from app.utils.thumbnail import generate_thumbnail
                    thumb_data = generate_thumbnail(image_data)
            except Exception as e:
                logger.warning(f"动态生成缩略图失败: {str(e)}")

        if not thumb_data:
            raise HTTPException(status_code=404, detail="缩略图数据不存在")

        return Response(content=thumb_data, media_type="image/jpeg")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取缩略图失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取缩略图失败")


# ==================== OCR审查相关API ====================

@router.post(
    "/{report_id}/review",
    response_model=OCRReviewListResponse,
    summary="提交OCR审查修正"
)
async def submit_ocr_review(
    report_id: int,
    review_data: OCRReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """
    提交对OCR结果的审查修正。

    用户可以对OCR识别的字段进行修正，系统会：
    1. 记录修正日志（原始值→修正值）
    2. 更新关联的医疗记录中的数据
    3. 将OCR状态更新为 reviewed
    """
    # 验证报告存在且属于当前用户
    result = await db.execute(
        select(ImageReport).where(
            ImageReport.report_id == report_id,
            ImageReport.account_id == current_user.account_id
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    if report.ocr_status not in ("pending_review", "completed", "failed"):
        raise HTTPException(status_code=400, detail="只能审查待确认、已完成或失败的OCR结果")

    # 确保 review_data 的 report_id 与路径参数一致
    review_data.report_id = report_id

    # 批量创建审查日志
    logs = []
    if review_data.corrections:
        for correction in review_data.corrections:
            log = OCRReviewLog(
                report_id=report_id,
                report_type=review_data.report_type,
                field_name=correction.field_name,
                original_value=correction.original_value,
                corrected_value=correction.corrected_value
            )
            db.add(log)
            logs.append(log)
    else:
        # 确认无误时创建汇总审计记录
        log = OCRReviewLog(
            report_id=report_id,
            report_type=review_data.report_type,
            field_name="__all__",
            original_value="",
            corrected_value="confirmed_no_changes"
        )
        db.add(log)
        logs.append(log)

    # 更新关联医疗记录中的修正值
    await _apply_corrections_to_medical_records(
        db, report, review_data.report_type, review_data.corrections
    )

    # 更新OCR状态
    report.ocr_status = "reviewed"
    await db.commit()

    # 刷新日志以获取ID和默认值
    for log in logs:
        await db.refresh(log)

    return OCRReviewListResponse(
        items=[OCRReviewResponse.model_validate(log) for log in logs],
        total=len(logs)
    )


@router.get(
    "/{report_id}/reviews",
    response_model=OCRReviewListResponse,
    summary="获取OCR审查记录"
)
async def get_ocr_reviews(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取指定上传报告的OCR审查修正记录"""
    # 验证报告存在且属于当前用户
    result = await db.execute(
        select(ImageReport).where(
            ImageReport.report_id == report_id,
            ImageReport.account_id == current_user.account_id
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    result = await db.execute(
        select(OCRReviewLog)
        .where(OCRReviewLog.report_id == report_id)
        .order_by(OCRReviewLog.reviewed_at.desc())
    )
    logs = result.scalars().all()

    return OCRReviewListResponse(
        items=[OCRReviewResponse.model_validate(log) for log in logs],
        total=len(logs)
    )


async def _apply_corrections_to_medical_records(
    db: AsyncSession,
    report: ImageReport,
    report_type: str,
    corrections: list
):
    """将修正值应用到关联的医疗记录"""
    # 构建字段名→修正值的映射
    correction_map = {c.field_name: c.corrected_value for c in corrections}

    if report_type == "lab" and report.related_check_id:
        # 修正检验报告明细
        result = await db.execute(
            select(MedicalCheckDetail).where(
                MedicalCheckDetail.medical_id == report.related_check_id
            )
        )
        details = result.scalars().all()
        for detail in details:
            if detail.index_name in correction_map:
                detail.index_value = correction_map[detail.index_name]

    elif report_type == "exam" and report.related_exam_id:
        # 修正检查报告 - 更新 extracted_info 中的字段
        if report.extracted_info and isinstance(report.extracted_info, dict):
            info = dict(report.extracted_info)
            for field_name, corrected_value in correction_map.items():
                if field_name in info:
                    info[field_name] = corrected_value
            report.extracted_info = info

        # 同步更新 MedicalExam.title（如果修正了 report_title）
        if 'report_title' in correction_map and correction_map['report_title']:
            exam_result = await db.execute(
                select(MedicalExam).where(MedicalExam.exam_id == report.related_exam_id)
            )
            exam = exam_result.scalar_one_or_none()
            if exam:
                exam.title = correction_map['report_title']

    elif report_type == "pathology" and report.related_pathology_id:
        # 病理报告修正 - 更新 extracted_info
        if report.extracted_info and isinstance(report.extracted_info, dict):
            info = dict(report.extracted_info)
            for field_name, corrected_value in correction_map.items():
                if field_name in info:
                    info[field_name] = corrected_value
            report.extracted_info = info
