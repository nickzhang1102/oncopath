"""静态文件服务路由

提供本地文件系统中的图片/缩略图/文档访问（需认证 + 所有权校验）。
"""
import re
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.user import LoginAccount
from app.models.image_report import ImageReport
from app.models.knowledge import KnowledgeDocument
from app.models.patient import Patient
from app.services.storage_service import get_storage_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["文件服务"])

# 只接受存储服务生成的单层 key，避免鉴权 ID 与规范化后的读取目标不一致。
_REPORT_BUCKETS = {"images", "thumbnails", "pathology"}
_DOCUMENT_BUCKETS = {"documents"}
_IMAGE_KEY_PATTERN = re.compile(r"^(\d+)\.[A-Za-z0-9]+$")
_THUMBNAIL_KEY_PATTERN = re.compile(r"^(\d+)_thumb\.[A-Za-z0-9]+$")
_DOCUMENT_KEY_PATTERN = re.compile(r"^(\d+)\.[A-Za-z0-9]+$")


def _extract_report_id(bucket: str, file_path: str) -> int | None:
    """从服务端生成的报告文件 key 中提取 report_id。

    支持格式:
    - images/123.jpg           → 123
    - thumbnails/123_thumb.jpg → 123
    - pathology/123.png         → 123
    """
    pattern = _THUMBNAIL_KEY_PATTERN if bucket == "thumbnails" else _IMAGE_KEY_PATTERN
    match = pattern.fullmatch(file_path)
    return int(match.group(1)) if match else None


def _extract_document_id(file_path: str) -> int | None:
    """从服务端生成的 documents 文件 key 中提取 doc_id。

    StorageService.save_document 使用 `{doc_id}.{ext}` 作为 key，因此文件服务也按
    这个稳定格式做所有权校验。
    """
    match = _DOCUMENT_KEY_PATTERN.fullmatch(file_path)
    return int(match.group(1)) if match else None


@router.get("/{bucket}/{file_path:path}")
async def serve_file(
    bucket: str,
    file_path: str,
    current_user: LoginAccount = Depends(get_current_user),
    db=Depends(get_db),
):
    """提供本地文件系统中的文件（需认证 + 所有权校验）

    校验逻辑:
    - images/thumbnails/pathology: 从文件路径提取 report_id，查 ImageReport.patient_id，
      再验证该 patient 属于当前用户（account_id）
    - documents: 从固定格式 key 提取 doc_id，并验证文档属于当前用户
    - 其他 bucket: 拒绝访问
    """
    storage = get_storage_service()

    # 所有权校验
    if bucket in _REPORT_BUCKETS:
        report_id = _extract_report_id(bucket, file_path)
        if report_id is None:
            raise HTTPException(status_code=400, detail="非法文件路径")

        # 单次 JOIN 查询验证 report 归属
        result = await db.execute(
            select(ImageReport.report_id)
            .join(Patient, ImageReport.patient_id == Patient.patient_id)
            .where(
                ImageReport.report_id == report_id,
                Patient.account_id == current_user.account_id,
            )
            .limit(1)
        )
        if not result.first():
            # 区分"不存在"和"无权访问"
            exists = await db.execute(
                select(ImageReport.report_id).where(ImageReport.report_id == report_id).limit(1)
            )
            if not exists.first():
                raise HTTPException(status_code=404, detail="文件不存在")
            raise HTTPException(status_code=403, detail="无权访问此文件")

    elif bucket in _DOCUMENT_BUCKETS:
        doc_id = _extract_document_id(file_path)
        if doc_id is None:
            raise HTTPException(status_code=400, detail="非法文件路径")

        result = await db.execute(
            select(KnowledgeDocument.doc_id)
            .where(
                KnowledgeDocument.doc_id == doc_id,
                KnowledgeDocument.account_id == current_user.account_id,
            )
            .limit(1)
        )
        if not result.first():
            exists = await db.execute(
                select(KnowledgeDocument.doc_id).where(KnowledgeDocument.doc_id == doc_id).limit(1)
            )
            if not exists.first():
                raise HTTPException(status_code=404, detail="文件不存在")
            raise HTTPException(status_code=403, detail="无权访问此文件")
    else:
        raise HTTPException(status_code=403, detail="不允许访问此类型的文件")

    # 读取文件
    try:
        data = await storage.read(bucket, file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在")
    except ValueError:
        raise HTTPException(status_code=400, detail="非法路径")

    if data is None:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 根据 extension 推断 content_type
    content_type = "application/octet-stream"
    lower_path = file_path.lower()
    if lower_path.endswith((".jpg", ".jpeg")):
        content_type = "image/jpeg"
    elif lower_path.endswith(".png"):
        content_type = "image/png"
    elif lower_path.endswith(".pdf"):
        content_type = "application/pdf"
    elif lower_path.endswith(".gif"):
        content_type = "image/gif"
    elif lower_path.endswith(".webp"):
        content_type = "image/webp"

    return Response(content=data, media_type=content_type)
