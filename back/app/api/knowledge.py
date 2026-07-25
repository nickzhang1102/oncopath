"""
知识库API模块
基于FastAPI重写的知识库接口，包含分类和文档管理功能
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_, and_, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
import logging
import os
import uuid
import shutil
import hashlib

from app.core.database import get_db
from app.core.config import settings
from app.api.auth import get_current_user
from app.core.rate_limit import limiter
from app.models.user import LoginAccount
from app.models.knowledge import KnowledgeCategory, KnowledgeDocument, KnowledgeAccessLog
from app.utils.knowledge_file_utils import get_full_path
from app.utils.office_converter import office_converter
from app.utils.time_utils import utc_isoformat
from app.schemas.knowledge import (
    KnowledgeCategoryCreate, KnowledgeCategoryUpdate, KnowledgeCategoryResponse,
    KnowledgeDocumentCreate, KnowledgeDocumentUpdate, KnowledgeDocumentResponse,
    KnowledgeDocumentListResponse, KnowledgeDocumentUploadResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _serialize_document(doc: KnowledgeDocument, category_name: str = None) -> dict:
    """序列化文档对象为响应字典"""
    data = {
        'doc_id': doc.doc_id,
        'doc_name': doc.doc_name,
        'doc_description': doc.doc_description,
        'category_id': doc.category_id,
        'category_name': category_name or (doc.category.category_name if doc.category else None),
        'file_name': doc.file_name,
        'file_size': doc.file_size,
        'file_type': doc.file_type,
        'mime_type': doc.mime_type,
        'download_count': doc.download_count,
        'view_count': doc.view_count,
        'is_public': doc.is_public,
        'tags': doc.tags.split(',') if doc.tags else [],
        'created_at': doc.created_at.isoformat() if doc.created_at else None,
        'updated_at': doc.updated_at.isoformat() if doc.updated_at else None,
        'has_preview': doc.preview_path is not None
    }
    return data

# 配置
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def allowed_file(filename: str) -> bool:
    """检查文件类型是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


# 扩展名→合法 MIME 类型映射（覆盖所有 ALLOWED_EXTENSIONS）
ALLOWED_MIME_MAP = {
    'txt': {'text/plain'},
    'pdf': {'application/pdf'},
    'png': {'image/png'},
    'jpg': {'image/jpeg'},
    'jpeg': {'image/jpeg'},
    'gif': {'image/gif'},
    'doc': {'application/msword'},
    'docx': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document'},
    'xls': {'application/vnd.ms-excel'},
    'xlsx': {'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'},
    'ppt': {'application/vnd.ms-powerpoint'},
    'pptx': {'application/vnd.openxmlformats-officedocument.presentationml.presentation'},
}


def validate_mime_type(filename: str, content_type: str) -> bool:
    """校验 MIME 类型与文件扩展名是否匹配

    Args:
        filename: 原始文件名
        content_type: 浏览器声明的 MIME 类型

    Returns:
        True 匹配或无法判断（扩展名不在映射表中），False 不匹配
    """
    ext = get_file_extension(filename)
    if not ext or ext not in ALLOWED_MIME_MAP:
        return True  # 扩展名不在表中，不拦截（由 allowed_file 兜底）
    # 取 MIME 主类型比较（忽略 charset 等参数）
    declared = (content_type or '').split(';')[0].strip().lower()
    return declared in ALLOWED_MIME_MAP[ext]


async def _check_document_duplicate(
    db: AsyncSession,
    account_id: int,
    file_hash: str,
) -> Optional[KnowledgeDocument]:
    """检查同一用户下是否已上传过相同内容的文件

    去重键: account_id + file_hash
    """
    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.account_id == account_id,
            KnowledgeDocument.file_hash == file_hash,
        ).limit(1)
    )
    return result.scalar_one_or_none()


# ============= 分类管理 =============
@router.get("/categories", response_model=List[KnowledgeCategoryResponse])
async def get_categories(
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取分类树"""
    try:
        # 获取当前用户的所有分类（不加载文档，使用子查询计数提升性能）
        result = await db.execute(
            select(KnowledgeCategory).where(
                KnowledgeCategory.account_id == current_user.account_id
            ).order_by(KnowledgeCategory.sort_order)
        )
        categories = result.scalars().all()

        # 子查询统计每个分类的文档数
        doc_count_result = await db.execute(
            select(
                KnowledgeDocument.category_id,
                func.count(KnowledgeDocument.doc_id).label('cnt')
            ).where(
                KnowledgeDocument.account_id == current_user.account_id
            ).group_by(KnowledgeDocument.category_id)
        )
        doc_count_map = {row.category_id: row.cnt for row in doc_count_result.all()}
        
        # 构建树形结构
        tree = []
        for category in categories:
            if category.parent_id is None:
                node = {
                    'category_id': category.category_id,
                    'category_name': category.category_name,
                    'parent_id': category.parent_id,
                    'sort_order': category.sort_order,
                    'is_expanded': category.is_expanded,
                    'account_id': category.account_id,
                    'document_count': doc_count_map.get(category.category_id, 0),
                    'created_at': category.created_at.isoformat() if category.created_at else None,
                    'updated_at': category.updated_at.isoformat() if category.updated_at else None,
                    'children': []
                }
                
                # 递归构建子分类
                def get_children(parent_id):
                    children = []
                    for cat in categories:
                        if cat.parent_id == parent_id:
                            child_node = {
                                'category_id': cat.category_id,
                                'category_name': cat.category_name,
                                'parent_id': cat.parent_id,
                                'sort_order': cat.sort_order,
                                'is_expanded': cat.is_expanded,
                                'account_id': cat.account_id,
                                'document_count': doc_count_map.get(cat.category_id, 0),
                                'created_at': cat.created_at.isoformat() if cat.created_at else None,
                                'updated_at': cat.updated_at.isoformat() if cat.updated_at else None,
                                'children': get_children(cat.category_id)
                            }
                            children.append(child_node)
                    return children
                
                node['children'] = get_children(category.category_id)
                tree.append(node)
        
        return tree
        
    except Exception as e:
        logger.error(f"获取分类失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取分类失败")


@router.post("/categories", response_model=KnowledgeCategoryResponse)
async def create_category(
    data: KnowledgeCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """创建分类"""
    try:
        # 检查同级分类名称是否重复
        stmt = select(KnowledgeCategory).where(
            KnowledgeCategory.account_id == current_user.account_id,
            KnowledgeCategory.parent_id == data.parent_id,
            KnowledgeCategory.category_name == data.category_name
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="同级分类下已存在相同名称的分类")
        
        # 创建分类
        category = KnowledgeCategory(
            category_name=data.category_name,
            parent_id=data.parent_id,
            sort_order=data.sort_order,
            is_expanded=data.is_expanded,
            account_id=current_user.account_id
        )
        
        db.add(category)
        await db.commit()
        await db.refresh(category)
        
        return {
            'category_id': category.category_id,
            'category_name': category.category_name,
            'parent_id': category.parent_id,
            'sort_order': category.sort_order,
            'is_expanded': category.is_expanded,
            'account_id': category.account_id,
            'document_count': 0,
            'created_at': utc_isoformat(category.created_at),
            'updated_at': utc_isoformat(category.updated_at),
            'children': []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"创建分类失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建分类失败")


@router.put("/categories/{category_id}", response_model=KnowledgeCategoryResponse)
async def update_category(
    category_id: int,
    data: KnowledgeCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """更新分类"""
    try:
        # 查找分类
        result = await db.execute(
            select(KnowledgeCategory).where(
                KnowledgeCategory.category_id == category_id,
                KnowledgeCategory.account_id == current_user.account_id
            )
        )
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")
        
        # 更新字段
        if data.category_name is not None:
            # 检查同级分类名称是否重复
            stmt = select(KnowledgeCategory).where(
                KnowledgeCategory.account_id == current_user.account_id,
                KnowledgeCategory.parent_id == category.parent_id,
                KnowledgeCategory.category_name == data.category_name,
                KnowledgeCategory.category_id != category_id
            )
            result = await db.execute(stmt)
            if result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="同级分类下已存在相同名称的分类")
            category.category_name = data.category_name
        
        if data.sort_order is not None:
            category.sort_order = data.sort_order
        if data.is_expanded is not None:
            category.is_expanded = data.is_expanded

        await db.commit()
        await db.refresh(category)

        return {
            'category_id': category.category_id,
            'category_name': category.category_name,
            'parent_id': category.parent_id,
            'sort_order': category.sort_order,
            'is_expanded': category.is_expanded,
            'account_id': category.account_id,
            'document_count': 0,
            'created_at': utc_isoformat(category.created_at),
            'updated_at': utc_isoformat(category.updated_at),
            'children': []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"更新分类失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新分类失败")


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """删除分类"""
    try:
        # 查找分类
        result = await db.execute(
            select(KnowledgeCategory).where(
                KnowledgeCategory.category_id == category_id,
                KnowledgeCategory.account_id == current_user.account_id
            )
        )
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")
        
        # 检查是否有子分类
        child_result = await db.execute(
            select(KnowledgeCategory).where(KnowledgeCategory.parent_id == category_id)
        )
        if child_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="请先删除子分类")
        
        # 检查是否有文档
        doc_result = await db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.category_id == category_id)
        )
        if doc_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="请先删除分类下的文档")
        
        await db.delete(category)
        await db.commit()
        
        return {"message": "删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"删除分类失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除分类失败")


# ============= 文档管理 =============
@router.get("/documents", response_model=KnowledgeDocumentListResponse)
async def get_documents(
    category_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    file_type: Optional[str] = Query(None),
    sort_by: str = Query('created_at'),
    sort_order: str = Query('desc'),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取文档列表"""
    try:
        # 构建查询
        stmt = select(KnowledgeDocument).options(
            selectinload(KnowledgeDocument.category)
        ).where(KnowledgeDocument.account_id == current_user.account_id)
        
        if category_id:
            stmt = stmt.where(KnowledgeDocument.category_id == category_id)
        
        if search:
            stmt = stmt.where(
                or_(
                    KnowledgeDocument.doc_name.contains(search),
                    KnowledgeDocument.doc_description.contains(search),
                    KnowledgeDocument.tags.contains(search)
                )
            )
        
        if file_type:
            stmt = stmt.where(KnowledgeDocument.file_type == file_type)
        
        # 排序（白名单映射，防止任意属性访问）
        SORT_FIELD_MAP = {
            'created_at': KnowledgeDocument.created_at,
            'updated_at': KnowledgeDocument.updated_at,
            'doc_name': KnowledgeDocument.doc_name,
            'file_size': KnowledgeDocument.file_size,
            'download_count': KnowledgeDocument.download_count,
        }
        sort_column = SORT_FIELD_MAP.get(sort_by, KnowledgeDocument.created_at)
        if sort_order == 'desc':
            stmt = stmt.order_by(desc(sort_column))
        else:
            stmt = stmt.order_by(sort_column)
        
        # 计算总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()
        
        # 分页
        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)
        
        result = await db.execute(stmt)
        documents = result.scalars().all()
        
        # 格式化返回数据
        doc_list = []
        for doc in documents:
            doc_list.append(_serialize_document(doc))
        
        return {
            'documents': doc_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
                'has_prev': page > 1,
                'has_next': page * per_page < total
            }
        }
        
    except Exception as e:
        logger.error(f"获取文档列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取文档列表失败")


@router.get("/documents/{doc_id}", response_model=KnowledgeDocumentResponse)
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取文档详情"""
    result = await db.execute(
        select(KnowledgeDocument).options(
            selectinload(KnowledgeDocument.category)
        ).where(
            KnowledgeDocument.doc_id == doc_id,
            KnowledgeDocument.account_id == current_user.account_id
        )
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    return _serialize_document(doc)


@router.get("/documents/{doc_id}/download")
async def download_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """下载知识库文档"""
    from fastapi.responses import FileResponse

    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.doc_id == doc_id,
            KnowledgeDocument.account_id == current_user.account_id
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if not doc.file_path:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 拼接完整路径
    full_path = get_full_path(doc.file_path)

    # 路径遍历防护：确保文件路径在存储根目录内
    storage_root_real = os.path.realpath(str(settings.STORAGE_PATH_RESOLVED))
    file_path_real = os.path.realpath(full_path)
    if not file_path_real.startswith(storage_root_real + os.sep) and file_path_real != storage_root_real:
        raise HTTPException(status_code=403, detail="非法文件路径")

    # 更新下载计数
    doc.download_count = (doc.download_count or 0) + 1

    # 记录访问日志
    access_log = KnowledgeAccessLog(
        doc_id=doc_id,
        account_id=current_user.account_id,
        access_type='download'
    )
    db.add(access_log)
    await db.commit()

    try:
        return FileResponse(
            path=full_path,
            filename=doc.file_name or os.path.basename(full_path),
            media_type=doc.mime_type or 'application/octet-stream',
            headers={'X-Content-Type-Options': 'nosniff'}
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在")


@router.post("/documents", response_model=KnowledgeDocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    category_id: Optional[int] = Form(None),
    doc_name: Optional[str] = Form(None),
    doc_description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    is_public: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """上传文档"""
    try:
        # 验证文件类型
        if not allowed_file(file.filename):
            raise HTTPException(status_code=400, detail="不支持的文件类型")

        # 验证 MIME 类型与扩展名匹配
        if not validate_mime_type(file.filename, file.content_type):
            raise HTTPException(status_code=400, detail="MIME类型与文件扩展名不匹配")

        # 验证分类（仅在提供时）
        if category_id is not None:
            cat_result = await db.execute(
                select(KnowledgeCategory).where(
                    KnowledgeCategory.category_id == category_id,
                    KnowledgeCategory.account_id == current_user.account_id
                )
            )
            if not cat_result.scalar_one_or_none():
                raise HTTPException(status_code=404, detail="分类不存在")

        # 创建上传目录（在存储根目录下）
        storage_root = str(settings.STORAGE_PATH_RESOLVED)
        upload_dir = os.path.join(storage_root, "knowledge", str(current_user.account_id))
        os.makedirs(upload_dir, exist_ok=True)

        # 生成唯一文件名
        file_ext = get_file_extension(file.filename)
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        full_path = os.path.join(upload_dir, unique_filename)

        # 相对路径（相对于 STORAGE_PATH，始终使用正斜杠保证跨平台兼容）
        relative_path = f"knowledge/{current_user.account_id}/{unique_filename}"

        # 读取内容并检查大小（先检查后写入，避免磁盘浪费）
        content = await file.read()
        file_size = len(content)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"文件大小超过限制（{MAX_FILE_SIZE // 1024 // 1024}MB）")

        # 计算 SHA-256 哈希
        file_hash = hashlib.sha256(content).hexdigest()

        # 重复校验
        existing = await _check_document_duplicate(db, current_user.account_id, file_hash)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"该文件已存在: {existing.doc_name}",
            )

        # 保存文件
        with open(full_path, "wb") as buffer:
            buffer.write(content)

        # 创建文档记录（file_path 存储相对路径）
        document = KnowledgeDocument(
            doc_name=doc_name or file.filename,
            doc_description=doc_description,
            category_id=category_id,
            file_path=relative_path,
            file_name=file.filename,
            file_size=file_size,
            file_type=file_ext,
            mime_type=file.content_type,
            file_hash=file_hash,
            summary_status='pending' if file_ext in ('txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx') else None,
            is_public=is_public,
            tags=tags,
            account_id=current_user.account_id
        )

        db.add(document)
        await db.commit()
        await db.refresh(document)

        # 上传后立即转换为HTML（Office/PDF/图片），用于移动端预览
        conversion_message = None
        if office_converter.is_supported(file_ext):
            try:
                success, html_content, error_msg = office_converter.convert_to_html(full_path, file_ext)
                if success and html_content:
                    html_filename = f"{document.doc_id}_preview.html"
                    html_full_path = os.path.join(upload_dir, html_filename)
                    with open(html_full_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    document.preview_path = os.path.join("knowledge", str(current_user.account_id), html_filename)
                    await db.commit()
                    conversion_message = "已转换为可预览格式"
                    logger.info(f"文档HTML转换成功: doc_id={document.doc_id}")
                else:
                    logger.warning(f"文档HTML转换失败: doc_id={document.doc_id}, error={error_msg}")
                    conversion_message = f"转换失败: {error_msg}"
            except Exception as conv_e:
                logger.error(f"文档HTML转换异常: doc_id={document.doc_id}, error={conv_e}")

        # 触发摘要生成（图片类不触发）
        if document.summary_status == 'pending':
            try:
                from app.tasks.knowledge_tasks import generate_knowledge_summary
                await generate_knowledge_summary(document.doc_id, full_path, file_ext)
                logger.info(f"摘要生成完成: doc_id={document.doc_id}")
            except Exception as task_e:
                logger.warning(f"摘要生成失败（不影响上传）: doc_id={document.doc_id}, error={task_e}")
                document.summary_status = 'failed'
                await db.commit()

        return {
            'doc_id': document.doc_id,
            'doc_name': document.doc_name,
            'file_name': document.file_name,
            'file_size': document.file_size,
            'file_type': document.file_type,
            'created_at': document.created_at.isoformat(),
            'has_preview': False,
            'conversion_message': conversion_message,
            'summary_status': document.summary_status,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"上传文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail="上传文档失败")


@router.put("/documents/{doc_id}", response_model=KnowledgeDocumentResponse)
async def update_document(
    doc_id: int,
    data: KnowledgeDocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """更新文档信息"""
    try:
        result = await db.execute(
            select(KnowledgeDocument)
            .options(selectinload(KnowledgeDocument.category))
            .where(
                KnowledgeDocument.doc_id == doc_id,
                KnowledgeDocument.account_id == current_user.account_id
            )
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        if data.doc_name is not None:
            doc.doc_name = data.doc_name
        if data.doc_description is not None:
            doc.doc_description = data.doc_description
        if data.tags is not None:
            doc.tags = data.tags
        if data.is_public is not None:
            doc.is_public = data.is_public
        
        if data.category_id is not None:
            # 验证新分类
            cat_result = await db.execute(
                select(KnowledgeCategory).where(
                    KnowledgeCategory.category_id == data.category_id,
                    KnowledgeCategory.account_id == current_user.account_id
                )
            )
            if not cat_result.scalar_one_or_none():
                raise HTTPException(status_code=404, detail="目标分类不存在")
            doc.category_id = data.category_id
        
        await db.commit()
        await db.refresh(doc)
        
        return _serialize_document(doc)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"更新文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新文档失败")


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """删除文档"""
    try:
        result = await db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.doc_id == doc_id,
                KnowledgeDocument.account_id == current_user.account_id
            )
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 删除物理文件（拼接完整路径）
        if doc.file_path:
            full_path = get_full_path(doc.file_path)
            if os.path.exists(full_path):
                os.remove(full_path)

        if doc.preview_path:
            full_preview_path = get_full_path(doc.preview_path)
            if os.path.exists(full_preview_path):
                os.remove(full_preview_path)

        await db.delete(doc)
        await db.commit()

        return {"message": "删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除文档失败")


@router.post("/documents/{doc_id}/generate-summary")
async def generate_summary(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """手动生成文档AI摘要"""
    try:
        result = await db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.doc_id == doc_id,
                KnowledgeDocument.account_id == current_user.account_id
            )
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 图片类不支持摘要
        if doc.file_type not in ('txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'):
            raise HTTPException(status_code=400, detail="该文件类型不支持AI摘要")

        # 更新状态为 pending
        doc.summary = None
        doc.summary_status = 'pending'
        await db.commit()

        # 触发摘要生成
        try:
            from app.tasks.knowledge_tasks import generate_knowledge_summary
            full_path = get_full_path(doc.file_path)
            await generate_knowledge_summary(doc.doc_id, full_path, doc.file_type)
            logger.info(f"手动生成摘要完成: doc_id={doc.doc_id}")
        except Exception as task_e:
            logger.warning(f"摘要生成失败: doc_id={doc.doc_id}, error={task_e}")
            doc.summary_status = 'failed'
            await db.commit()

        return {"message": "摘要生成完成", "summary_status": doc.summary_status}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"生成摘要失败: {str(e)}")
        raise HTTPException(status_code=500, detail="生成摘要失败")


@router.get("/search")
@limiter.limit("20/minute")
async def search_documents(
    request: Request,
    q: str = Query(..., min_length=1, description="搜索关键词"),
    category_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """搜索文档"""
    try:
        stmt = select(KnowledgeDocument).options(
            selectinload(KnowledgeDocument.category)
        ).where(
            KnowledgeDocument.account_id == current_user.account_id,
            or_(
                KnowledgeDocument.doc_name.contains(q),
                KnowledgeDocument.doc_description.contains(q),
                KnowledgeDocument.tags.contains(q)
            )
        )
        
        if category_id:
            stmt = stmt.where(KnowledgeDocument.category_id == category_id)
        
        stmt = stmt.order_by(desc(KnowledgeDocument.created_at)).limit(limit)
        
        result = await db.execute(stmt)
        documents = result.scalars().all()
        
        return [{
            'doc_id': doc.doc_id,
            'doc_name': doc.doc_name,
            'doc_description': doc.doc_description,
            'category_id': doc.category_id,
            'category_name': doc.category.category_name if doc.category else None,
            'file_type': doc.file_type,
            'created_at': utc_isoformat(doc.created_at)
        } for doc in documents]
        
    except Exception as e:
        logger.error(f"搜索文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail="搜索文档失败")
