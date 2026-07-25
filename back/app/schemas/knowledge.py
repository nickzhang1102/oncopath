"""知识库相关Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============= 分类相关 =============
class KnowledgeCategoryBase(BaseModel):
    category_name: str = Field(..., max_length=100, description="分类名称")
    parent_id: Optional[int] = Field(None, description="父分类ID")
    sort_order: int = Field(0, description="排序")
    is_expanded: bool = Field(False, description="是否展开")


class KnowledgeCategoryCreate(KnowledgeCategoryBase):
    pass


class KnowledgeCategoryUpdate(BaseModel):
    category_name: Optional[str] = Field(None, max_length=100)
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None
    is_expanded: Optional[bool] = None


class KnowledgeCategoryResponse(KnowledgeCategoryBase):
    category_id: int
    account_id: int
    document_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    children: List['KnowledgeCategoryResponse'] = []

    class Config:
        from_attributes = True


# ============= 文档相关 =============
class KnowledgeDocumentBase(BaseModel):
    doc_name: str = Field(..., max_length=200, description="文档名称")
    doc_description: Optional[str] = Field(None, description="文档描述")
    category_id: Optional[int] = Field(None, description="分类ID")
    is_public: bool = Field(True, description="是否公开")
    tags: Optional[str] = Field(None, description="标签，逗号分隔")


class KnowledgeDocumentCreate(KnowledgeDocumentBase):
    pass


class KnowledgeDocumentUpdate(BaseModel):
    doc_name: Optional[str] = Field(None, max_length=200)
    doc_description: Optional[str] = None
    category_id: Optional[int] = None
    is_public: Optional[bool] = None
    tags: Optional[str] = None


class KnowledgeDocumentResponse(BaseModel):
    doc_id: int
    doc_name: str
    doc_description: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    mime_type: Optional[str] = None
    download_count: int = 0
    view_count: int = 0
    is_public: bool = True
    tags: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    has_preview: bool = False
    summary: Optional[str] = None
    summary_status: Optional[str] = None

    class Config:
        from_attributes = True


class KnowledgeDocumentListResponse(BaseModel):
    documents: List[KnowledgeDocumentResponse]
    pagination: dict


# ============= 文档上传 =============
class KnowledgeDocumentUploadResponse(BaseModel):
    doc_id: int
    doc_name: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    created_at: Optional[datetime] = None
    has_preview: bool = False
    conversion_message: Optional[str] = None
    summary_status: Optional[str] = None


# ============= 访问日志 =============
class KnowledgeAccessLogResponse(BaseModel):
    log_id: int
    doc_id: int
    account_id: int
    access_type: str
    ip_address: Optional[str] = None
    access_time: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============= 搜索 =============
class KnowledgeSearchQuery(BaseModel):
    search: Optional[str] = None
    category_id: Optional[int] = None
    file_type: Optional[str] = None
    sort_by: str = 'created_at'
    sort_order: str = 'desc'
    page: int = 1
    per_page: int = 20


# 更新forward reference
KnowledgeCategoryResponse.model_rebuild()