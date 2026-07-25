"""
知识库文档预览模块
包含文档预览、下载和各种文件类型的预览处理
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import os
from typing import Optional

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import LoginAccount
from app.models.knowledge import KnowledgeDocument, KnowledgeAccessLog
from app.utils.office_converter import office_converter
from app.utils.knowledge_file_utils import (
    encode_filename_for_header, format_file_size,
    get_file_extension, is_image_file, is_office_file,
    is_pdf_file, is_text_file, get_mime_type_by_extension
)
from app.utils.knowledge_html_generators import (
    create_text_preview_html, create_office_preview_html, create_pdf_preview_html,
    create_fullscreen_image_preview_html, create_fullscreen_pdf_viewer_html
)
from app.core.config import settings
from app.core.security import verify_token
from app.utils.knowledge_file_utils import get_full_path

logger = logging.getLogger(__name__)
router = APIRouter()


def _html_with_frame_header(content: str) -> HTMLResponse:
    """返回带 X-Frame-Options HTTP 头的 HTML 响应（仅允许同源嵌入）"""
    return HTMLResponse(
        content=content,
        media_type="text/html",
        headers={"X-Frame-Options": "SAMEORIGIN"},
    )


async def get_current_user_for_preview(
    request: Request,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> LoginAccount:
    """
    预览专用认证依赖
    支持 Header + URL 参数两种方式传递 token（iframe/图片场景）
    """
    # 1. 优先从 Authorization header 获取
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token_str = auth_header[7:]
    elif token:
        # 2. 从 URL 参数获取（iframe 场景）
        token_str = token
    else:
        raise HTTPException(status_code=401, detail="Token is missing")

    # 3. 验证 token（返回 account_id）
    account_id = verify_token(token_str)
    if not account_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 4. 查询用户
    result = await db.execute(
        select(LoginAccount).where(LoginAccount.account_id == account_id)
    )
    current_user = result.scalar_one_or_none()

    if not current_user:
        raise HTTPException(status_code=401, detail="Account not found")

    # 5. 检查账号状态（使用 status 字段）
    if current_user.status != "active":
        raise HTTPException(status_code=401, detail="Account is inactive")

    return current_user


@router.get("/documents/{doc_id}/preview")
async def preview_document(
    doc_id: int,
    request: Request,
    direct: bool = False,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user_for_preview)
):
    """预览文档"""
    try:
        # 查找文档并验证权限
        result = await db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.doc_id == doc_id,
                KnowledgeDocument.account_id == current_user.account_id
            )
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 验证文件路径
        if not document.file_path:
            raise HTTPException(status_code=404, detail="文件不存在")

        # 拼接完整路径
        file_path = get_full_path(document.file_path)
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            raise HTTPException(status_code=404, detail="文件不存在")

        # 路径遍历防护（使用存储根目录）
        storage_root_real = os.path.realpath(str(settings.STORAGE_PATH_RESOLVED))
        file_path_real = os.path.realpath(file_path)
        logger.info(f"路径验证: storage_root={storage_root_real}, file_path={file_path_real}")
        if not file_path_real.startswith(storage_root_real + os.sep) and file_path_real != storage_root_real:
            logger.error(f"路径遍历防护失败: storage_root={storage_root_real}, file_path={file_path_real}")
            raise HTTPException(status_code=403, detail="非法文件路径")

        # 检查是否为直接文件请求（图片等）
        if direct:
            file_ext = get_file_extension(document.file_name or document.doc_name) or (document.file_type or '').lower().lstrip('.')
            mime_type = get_mime_type_by_extension(file_ext)
            logger.info(f"直接文件请求 doc_id={doc_id}, file_ext='{file_ext}', mime_type='{mime_type}', file_path='{file_path}', exists={os.path.exists(file_path)}")

            # 记录访问日志
            access_log = KnowledgeAccessLog(
                doc_id=doc_id,
                account_id=current_user.account_id,
                access_type='preview'
            )
            db.add(access_log)
            document.view_count = (document.view_count or 0) + 1
            await db.commit()

            return FileResponse(
                path=file_path,
                media_type=mime_type,
                filename=document.file_name or document.doc_name,
                headers={"Content-Disposition": f'inline; filename="{document.file_name or document.doc_name}"'}
            )

        # 获取文件类型信息
        file_ext = get_file_extension(document.file_name or document.doc_name) or (document.file_type or '').lower().lstrip('.')
        logger.info(f"预览文档 doc_id={doc_id}, direct={direct}, file_ext='{file_ext}', file_name={document.file_name}, file_type={document.file_type}, file_path='{file_path}', exists={os.path.exists(file_path)}")

        # 根据文件类型处理
        if is_image_file(file_ext):
            logger.info(f"路由到图片预览: doc_id={doc_id}")
            return await handle_image_preview(request, document, file_path, db)
        elif is_pdf_file(file_ext):
            logger.info(f"路由到PDF预览: doc_id={doc_id}")
            return await handle_pdf_preview(request, document, file_path, db)
        elif is_text_file(file_ext):
            return await handle_text_preview(document, file_path, file_ext, db)
        elif is_office_file(file_ext):
            return await handle_office_preview(document, file_path, file_ext, db)
        else:
            # 其他文件类型，返回下载信息
            logger.warning(f"不支持预览的文件类型: doc_id={doc_id}, file_ext='{file_ext}', file_name={document.file_name}")
            return JSONResponse({
                "code": 200,
                "message": "文件无法直接预览",
                "data": {
                    "doc_id": document.doc_id,
                    "doc_name": document.doc_name,
                    "file_name": document.file_name,
                    "file_type": document.file_type,
                    "file_size": document.file_size,
                    "download_url": f"/api/v1/knowledge/documents/{doc_id}/download",
                    "message": "请下载后查看"
                }
            })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预览文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"预览文档失败: {str(e)}")


async def handle_image_preview(request: Request, document, file_path: str, db: AsyncSession):
    """处理图片预览"""
    logger.info(f"图片预览: {document.doc_id}, 文件路径: {file_path}")
    logger.info(f"preview_path字段: {getattr(document, 'preview_path', '无')}")

    # 检查是否有预生成的 HTML 预览（并验证路径）
    if hasattr(document, 'preview_path') and document.preview_path:
        full_preview_path = get_full_path(document.preview_path)
        preview_path_real = os.path.realpath(full_preview_path)
        storage_root_real = os.path.realpath(str(settings.STORAGE_PATH_RESOLVED))
        logger.info(f"preview_path验证: storage_root={storage_root_real}, preview_path={preview_path_real}")

        # 路径验证：preview_path 也必须在存储根目录下
        if (preview_path_real.startswith(storage_root_real + os.sep) or preview_path_real == storage_root_real) and os.path.exists(full_preview_path):
            logger.info(f"返回图片HTML预览: {full_preview_path}")
            try:
                with open(full_preview_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # 记录访问日志
                access_log = KnowledgeAccessLog(
                    doc_id=document.doc_id,
                    account_id=document.account_id,
                    access_type='preview'
                )
                db.add(access_log)
                document.view_count = (document.view_count or 0) + 1
                await db.commit()

                return _html_with_frame_header(html_content)
            except Exception as e:
                logger.error(f"读取图片HTML预览文件失败: {str(e)}")
        else:
            logger.warning(f"preview_path路径验证失败或文件不存在，跳过预生成HTML: {preview_path_real}")

    # 创建全屏图片预览 HTML
    try:
        # 从请求中获取 token（支持 header + URL 参数）
        auth_header = request.headers.get('Authorization')
        token_param = request.query_params.get('token')
        token = None

        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
        elif token_param:
            token = token_param

        # 构建图片 URL（通过前端代理）
        frontend_host = request.headers.get('Host', 'localhost:3000')
        scheme = 'https' if request.url.scheme == 'https' else 'http'

        # 智能构建后端 URL
        base_url = f"{scheme}://{frontend_host}/api/v1"

        if token:
            image_url = f"{base_url}/knowledge/documents/{document.doc_id}/preview?direct=true&token={token}"
        else:
            image_url = f"{base_url}/knowledge/documents/{document.doc_id}/preview?direct=true"

        logger.info(f"构建图片预览URL: doc_id={document.doc_id}, token_in_query={bool(token)}")

        # 生成全屏图片预览 HTML
        html_content = create_fullscreen_image_preview_html(document, image_url)

        # 记录访问日志
        access_log = KnowledgeAccessLog(
            doc_id=document.doc_id,
            account_id=document.account_id,
            access_type='preview'
        )
        db.add(access_log)
        document.view_count = (document.view_count or 0) + 1
        await db.commit()

        return _html_with_frame_header(html_content)

    except Exception as e:
        logger.error(f"创建图片预览HTML失败: {str(e)}")
        # 降级：直接返回图片文件
        file_ext = get_file_extension(document.file_name or document.doc_name)
        mime_type = get_mime_type_by_extension(file_ext)

        access_log = KnowledgeAccessLog(
            doc_id=document.doc_id,
            account_id=document.account_id,
            access_type='preview'
        )
        db.add(access_log)
        document.view_count = (document.view_count or 0) + 1
        await db.commit()

        return FileResponse(path=file_path, media_type=mime_type)


async def handle_pdf_preview(request: Request, document, file_path: str, db: AsyncSession):
    """处理PDF预览"""
    logger.info(f"PDF预览: {document.doc_id}, 文件路径: {file_path}")

    # 检查是否有预生成的 HTML 预览
    if hasattr(document, 'preview_path') and document.preview_path:
        full_preview_path = get_full_path(document.preview_path)
        if os.path.exists(full_preview_path):
            logger.info(f"返回PDF HTML预览: {full_preview_path}")
            try:
                with open(full_preview_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                access_log = KnowledgeAccessLog(
                    doc_id=document.doc_id,
                    account_id=document.account_id,
                    access_type='preview'
                )
                db.add(access_log)
                document.view_count = (document.view_count or 0) + 1
                await db.commit()

                return _html_with_frame_header(html_content)
            except Exception as e:
                logger.error(f"读取PDF HTML预览文件失败: {str(e)}")

    # 创建全屏 PDF 查看器
    try:
        # 从请求中获取 token（支持 header + URL 参数）
        auth_header = request.headers.get('Authorization')
        token_param = request.query_params.get('token')
        token = None

        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
        elif token_param:
            token = token_param

        # 构建 PDF URL
        frontend_host = request.headers.get('Host', 'localhost:3000')
        scheme = 'https' if request.url.scheme == 'https' else 'http'
        base_url = f"{scheme}://{frontend_host}/api/v1"

        if token:
            pdf_url = f"{base_url}/knowledge/documents/{document.doc_id}/preview?direct=true&token={token}"
        else:
            pdf_url = f"{base_url}/knowledge/documents/{document.doc_id}/preview?direct=true"

        logger.info(f"构建PDF预览URL: doc_id={document.doc_id}, token_in_query={bool(token)}")

        # 生成全屏 PDF 查看器 HTML
        html_content = create_fullscreen_pdf_viewer_html(document, pdf_url)

        access_log = KnowledgeAccessLog(
            doc_id=document.doc_id,
            account_id=document.account_id,
            access_type='preview'
        )
        db.add(access_log)
        document.view_count = (document.view_count or 0) + 1
        await db.commit()

        return _html_with_frame_header(html_content)

    except Exception as e:
        logger.error(f"创建PDF查看器失败: {str(e)}")
        # 降级：返回 PDF 文件
        access_log = KnowledgeAccessLog(
            doc_id=document.doc_id,
            account_id=document.account_id,
            access_type='preview'
        )
        db.add(access_log)
        document.view_count = (document.view_count or 0) + 1
        await db.commit()

        return FileResponse(path=file_path, media_type="application/pdf")


async def handle_text_preview(document, file_path: str, file_ext: str, db: AsyncSession):
    """处理文本文件预览"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 创建 HTML 响应
        html_content = create_text_preview_html(document, content, file_ext)

        access_log = KnowledgeAccessLog(
            doc_id=document.doc_id,
            account_id=document.account_id,
            access_type='preview'
        )
        db.add(access_log)
        document.view_count = (document.view_count or 0) + 1
        await db.commit()

        return _html_with_frame_header(html_content)

    except UnicodeDecodeError:
        # 不能以 UTF-8 解码，返回下载信息
        return JSONResponse({
            "code": 200,
            "message": "文件编码不支持在线预览",
            "data": {
                "doc_id": document.doc_id,
                "doc_name": document.doc_name,
                "file_type": document.file_type,
                "download_url": f"/api/v1/knowledge/documents/{document.doc_id}/download",
                "message": "请下载后查看"
            }
        })


async def handle_office_preview(document, file_path: str, file_ext: str, db: AsyncSession):
    """处理Office文档预览"""
    logger.info(f"Office文件 {document.doc_id}: 检查HTML预览")

    # 检查是否有预生成的 HTML 预览
    if hasattr(document, 'preview_path') and document.preview_path:
        full_preview_path = get_full_path(document.preview_path)
        if os.path.exists(full_preview_path):
            logger.info(f"返回Office HTML预览: {full_preview_path}")
            try:
                with open(full_preview_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                access_log = KnowledgeAccessLog(
                    doc_id=document.doc_id,
                    account_id=document.account_id,
                    access_type='preview'
                )
                db.add(access_log)
                document.view_count = (document.view_count or 0) + 1
                await db.commit()

                return _html_with_frame_header(html_content)
            except Exception as e:
                logger.error(f"读取Office HTML预览文件失败: {str(e)}")

    # 尝试实时转换
    logger.info(f"尝试实时转换Office文档: {document.doc_id}, 文件类型: {file_ext}")
    try:
        success, html_content, error_msg = office_converter.convert_to_html(file_path, file_ext)

        logger.info(f"转换结果: success={success}, error_msg={error_msg}")

        if success and html_content:
            # 保存转换结果
            try:
                # file_path 已是完整路径（由 preview_document 传入）
                upload_dir = os.path.dirname(file_path)
                html_filename = f"{document.doc_id}_preview.html"
                html_full_path = os.path.join(upload_dir, html_filename)

                # 相对路径（统一使用正斜杠，保证跨平台兼容）
                file_dir = document.file_path.replace("\\", "/").rsplit("/", 1)[0] if "/" in document.file_path.replace("\\", "/") else ""
                html_relative_path = f"{file_dir}/{html_filename}" if file_dir else html_filename

                with open(html_full_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                # 更新数据库记录（存储相对路径）
                document.preview_path = html_relative_path
                await db.commit()

                logger.info(f"实时转换成功并保存: {html_full_path}")
            except Exception as save_e:
                logger.error(f"保存转换结果失败: {str(save_e)}")

            # 记录访问日志
            access_log = KnowledgeAccessLog(
                doc_id=document.doc_id,
                account_id=document.account_id,
                access_type='preview'
            )
            db.add(access_log)
            document.view_count = (document.view_count or 0) + 1
            await db.commit()

            return _html_with_frame_header(html_content)
        else:
            logger.error(f"实时转换失败: {error_msg}")
            # 转换失败，返回信息页面
            html_content = create_office_preview_html(document, file_ext)

            access_log = KnowledgeAccessLog(
                doc_id=document.doc_id,
                account_id=document.account_id,
                access_type='preview'
            )
            db.add(access_log)
            document.view_count = (document.view_count or 0) + 1
            await db.commit()

            return _html_with_frame_header(html_content)

    except Exception as e:
        logger.error(f"实时转换异常: {str(e)}")
        # 转换异常，返回信息页面
        html_content = create_office_preview_html(document, file_ext)

        access_log = KnowledgeAccessLog(
            doc_id=document.doc_id,
            account_id=document.account_id,
            access_type='preview'
        )
        db.add(access_log)
        document.view_count = (document.view_count or 0) + 1
        await db.commit()

        return _html_with_frame_header(html_content)
