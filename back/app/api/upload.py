"""图片上传API - 从原版Flask迁移到FastAPI"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.core.rate_limit import limiter
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.core.redis import redis_client
from app.api.auth import get_current_user
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.medical import MedicalCheck, MedicalCheckDetail, MedicalExam

router = APIRouter()
logger = logging.getLogger(__name__)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# 文件大小限制（50MB）
MAX_FILE_SIZE = 50 * 1024 * 1024


def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


async def process_upload_task(
    file_path: str,
    report_type: str,
    category: str,
    hospital: str,
    medical_date: datetime,
    patient_id: int,
    session_id: str
):
    """后台任务：处理上传的报告"""
    status_key = f"upload:status:{session_id}"
    try:
        logger.info(f"Session {session_id}: 开始处理上传报告")

        # 更新状态为处理中
        await redis_client.set(
            status_key,
            json.dumps({"status": "processing", "progress": 50}),
            ex=3600
        )

        # 初始化OCR集成服务
        from app.services.ocr.ocr_integration_service import OCRIntegrationService
        ocr_service = OCRIntegrationService()

        # 处理报告
        result = None
        if report_type == 'check':
            result = await ocr_service.process_check_report(
                file_path=file_path,
                category=category,
                hospital=hospital,
                medical_date=medical_date,
                patient_id=patient_id
            )
        elif report_type == 'exam':
            result = await ocr_service.process_exam_report(
                file_path=file_path,
                category=category,
                hospital=hospital,
                medical_date=medical_date,
                patient_id=patient_id
            )
        else:
            raise ValueError(f"不支持的报告类型: {report_type}")

        logger.info(f"Session {session_id}: 处理完成 - {result}")

        # 更新状态为完成
        result_data = {"status": "completed", "progress": 100}
        if isinstance(result, dict):
            result_data.update(result)
        await redis_client.set(
            status_key,
            json.dumps(result_data),
            ex=3600
        )

        return result

    except Exception as e:
        logger.error(f"Session {session_id}: 处理失败 - {str(e)}", exc_info=True)
        # 更新状态为失败
        await redis_client.set(
            status_key,
            json.dumps({"status": "failed", "error": str(e)}),
            ex=3600
        )
        raise

    finally:
        # 清理临时文件
        if os.path.exists(file_path):
            os.unlink(file_path)
            try:
                os.rmdir(os.path.dirname(file_path))
            except OSError:
                pass


@router.post("/upload")
@limiter.limit("10/minute")
async def upload_report(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    report_type: str = Form(...),
    category: str = Form(...),
    hospital: str = Form(...),
    medical_date: str = Form(...),
    patient_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """
    上传医疗报告图片

    上传医疗报告图片并自动触发OCR识别和指标匹配处理。

    支持的报告类型：
    - **check**: 检验报告（血液检验、生化检验等）
      - OCR识别 → 指标匹配 → 创建MedicalCheck记录
      - 返回medical_id, items_count, matched_count
    - **exam**: 检查报告（CT、MRI、超声等）
      - OCR识别 → 文本提取 → 创建MedicalExam记录
      - 返回exam_id, exam_info

    处理流程：
    1. 验证文件格式和大小
    2. 验证患者归属权限
    3. 保存临时文件
    4. 后台异步处理（OCR + 指标匹配）
    5. 返回会话ID用于状态查询

    Args:
        background_tasks: FastAPI后台任务管理器
        file: 报告图片文件
            - 格式: JPG, PNG, JPEG
            - 大小: 最大50MB
        report_type: 报告类型
            - 可选值: "check"（检验报告）, "exam"（检查报告）
            - 必填
        category: 报告分类key
            - 如: blood_routine, biochemistry, tumor_marker 等
            - 必填
        hospital: 医院名称
            - 必填
        medical_date: 医疗日期
            - 格式: YYYY-MM-DD
            - 必填
        patient_id: 患者ID
            - 必须属于当前用户
            - 必填
        db: 数据库会话（自动注入）
        current_user: 当前登录用户（自动注入）

    Returns:
        dict: 上传结果
        ```json
        {
            "status": "success",
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "message": "文件上传成功，正在处理中..."
        }
        ```

    Raises:
        HTTPException:
            - 400: 文件格式不支持、参数错误
            - 401: 未授权访问
            - 404: 患者不存在
            - 413: 文件大小超限
            - 500: 服务器内部错误

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/upload" \\
          -H "Authorization: Bearer <token>" \\
          -F "file=@report.jpg" \\
          -F "report_type=check" \\
          -F "category=blood_routine" \\
          -F "hospital=北京医院" \\
          -F "medical_date=2026-03-18" \\
          -F "patient_id=1"
        ```
    """
    try:
        # 生成会话ID
        session_id = str(uuid.uuid4())

        # 验证文件格式
        if not file.filename or not allowed_file(file.filename):
            raise HTTPException(
                status_code=400,
                detail="不支持的文件格式，请上传PNG、JPG或JPEG格式的图片"
            )

        # 验证报告类型
        if report_type not in ['check', 'exam']:
            raise HTTPException(
                status_code=400,
                detail="请选择正确的报告类型（check或exam）"
            )

        # 验证患者归属
        result = await db.execute(
            select(Patient).where(
                Patient.patient_id == patient_id,
                Patient.account_id == current_user.account_id
            )
        )
        patient = result.scalar_one_or_none()
        if not patient:
            raise HTTPException(
                status_code=404,
                detail="患者不存在或无权访问"
            )

        # 验证医疗类型
        if not category or not category.strip():
            raise HTTPException(
                status_code=400,
                detail="请选择报告分类"
            )

        # 解析日期
        try:
            parsed_date = datetime.strptime(medical_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="日期格式错误，请使用YYYY-MM-DD格式"
            )

        # 流式读取文件并写入临时文件。文件名由服务端生成，避免客户端文件名造成路径穿越。
        temp_dir = tempfile.mkdtemp()
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        temp_file_path = os.path.join(temp_dir, f"{session_id}.{file_ext}")

        file_size = 0
        CHUNK_SIZE = 1024 * 1024  # 1MB chunks

        with open(temp_file_path, 'wb') as f:
            while chunk := await file.read(CHUNK_SIZE):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    # 清理临时文件
                    os.unlink(temp_file_path)
                    os.rmdir(temp_dir)
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件大小超过限制（最大{MAX_FILE_SIZE // (1024*1024)}MB）"
                    )
                f.write(chunk)

        if file_size == 0:
            os.unlink(temp_file_path)
            os.rmdir(temp_dir)
            raise HTTPException(status_code=400, detail="上传的文件为空")

        logger.info(f"Session {session_id}: 文件验证通过，大小: {file_size / 1024:.1f} KB")
        logger.info(f"Session {session_id}: 文件已保存到临时目录")

        # 添加后台任务处理报告
        background_tasks.add_task(
            process_upload_task,
            temp_file_path,
            report_type,
            category,
            hospital,
            parsed_date,
            patient_id,
            session_id
        )

        # 存储初始上传状态到 Redis
        await redis_client.set(
            f"upload:status:{session_id}",
            json.dumps({"status": "processing", "progress": 0}),
            ex=3600  # 1小时过期
        )

        return {
            "status": "success",
            "session_id": session_id,
            "message": "文件上传成功，正在处理中..."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传报告失败: {str(e)}", exc_info=True)
        if settings.DEBUG:
            raise HTTPException(
                status_code=500,
                detail=f"上传失败: {str(e)}"
            )
        raise HTTPException(
            status_code=500,
            detail="上传失败，请稍后重试"
        )


@router.get("/upload/status/{session_id}")
async def get_upload_status(
    session_id: str,
    current_user: LoginAccount = Depends(get_current_user)
):
    """
    查询上传处理状态

    查询图片上传后的OCR识别和指标匹配处理状态。

    处理状态：
    - **processing**: 正在处理中（OCR识别、指标匹配）
    - **completed**: 处理完成
    - **failed**: 处理失败

    处理结果（completed状态）：
    - 检验报告（check）：
      - medical_id: 创建的检验记录ID
      - items_count: 识别到的指标总数
      - matched_count: 成功匹配的指标数
    - 检查报告（exam）：
      - exam_id: 创建的检查记录ID
      - exam_info: 检查描述信息

    Args:
        session_id: 上传会话ID（由/upload接口返回）
        current_user: 当前登录用户（自动注入）

    Returns:
        dict: 处理状态
        ```json
        {
            "status": "completed",
            "message": "处理完成",
            "result": {
                "medical_id": 123,
                "items_count": 15,
                "matched_count": 12
            }
        }
        ```

    Raises:
        HTTPException:
            - 401: 未授权访问
            - 404: 会话不存在

    Example:
        ```bash
        curl -X GET "http://localhost:8000/api/upload/status/550e8400-e29b-41d4-a716-446655440000" \\
          -H "Authorization: Bearer <token>"
        ```

    Note:
        使用Redis存储处理状态，1小时后自动过期。
    """
    status_data = await redis_client.get(f"upload:status:{session_id}")
    if status_data:
        return json.loads(status_data)
    return {"status": "not_found", "message": "上传会话不存在或已过期"}
