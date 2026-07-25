"""知识库相关数据模型

包含:
- KnowledgeCategory: 知识库分类
- KnowledgeDocument: 知识库文档
- KnowledgeAccessLog: 知识库访问日志
- KnowledgeConfig: 知识库配置
- PromptConfig: AI提示词配置

注意: ImageReport 和 ImageCategory 已移动到 image_report.py
"""
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class KnowledgeCategory(Base):
    """知识库分类表"""
    __tablename__ = "knowledge_category"

    category_id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(100), nullable=False, comment='分类名称')
    parent_id = Column(Integer, ForeignKey('knowledge_category.category_id', ondelete='SET NULL'), comment='父分类ID')
    sort_order = Column(Integer, default=0, comment='排序')
    is_expanded = Column(Boolean, default=False, comment='是否展开')
    account_id = Column(Integer, ForeignKey('login_account.account_id', ondelete='CASCADE'), comment='账号ID')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    # 关系
    children = relationship("KnowledgeCategory", back_populates="parent_category", remote_side=[category_id])
    parent_category = relationship("KnowledgeCategory", back_populates="children", foreign_keys=[parent_id])
    documents = relationship("KnowledgeDocument", back_populates="category")

    # 索引
    __table_args__ = (
        Index('idx_knowledge_category_parent', 'parent_id'),
        Index('idx_knowledge_category_account', 'account_id'),
    )

    def __repr__(self):
        return f"<KnowledgeCategory(category_name={self.category_name})>"


class KnowledgeDocument(Base):
    """知识库文档表"""
    __tablename__ = "knowledge_document"

    doc_id = Column(Integer, primary_key=True, index=True)
    doc_name = Column(String(200), nullable=False, comment='文档名称')
    doc_description = Column(Text, comment='文档描述')
    category_id = Column(Integer, ForeignKey('knowledge_category.category_id', ondelete='SET NULL'), comment='分类ID')
    file_path = Column(String(500), comment='文件相对路径（相对于 STORAGE_PATH）')
    file_name = Column(String(200), comment='文件名')
    file_size = Column(Integer, comment='文件大小')
    file_type = Column(String(50), comment='文件类型')
    mime_type = Column(String(100), comment='MIME类型')
    file_hash = Column(String(64), comment='文件哈希(SHA-256)')
    preview_path = Column(String(500), comment='预览路径')
    summary = Column(Text, comment='AI生成摘要')
    summary_status = Column(String(20), comment='摘要状态: pending/completed/failed')
    download_count = Column(Integer, default=0, comment='下载次数')
    view_count = Column(Integer, default=0, comment='查看次数')
    is_public = Column(Boolean, default=True, comment='是否公开')
    tags = Column(Text, comment='标签')
    account_id = Column(Integer, ForeignKey('login_account.account_id', ondelete='CASCADE'), comment='账号ID')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    # 关系
    category = relationship("KnowledgeCategory", back_populates="documents")
    access_logs = relationship("KnowledgeAccessLog", back_populates="document", cascade="all, delete-orphan", passive_deletes=True)

    # 索引 + 唯一约束
    __table_args__ = (
        Index('idx_knowledge_document_category', 'category_id'),
        Index('idx_knowledge_document_account', 'account_id'),
        UniqueConstraint('account_id', 'file_hash', name='uq_knowledge_doc_account_hash'),
    )

    def __repr__(self):
        return f"<KnowledgeDocument(doc_name={self.doc_name})>"


class KnowledgeAccessLog(Base):
    """知识库访问日志表"""
    __tablename__ = "knowledge_access_log"

    log_id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey('knowledge_document.doc_id', ondelete='CASCADE'), nullable=False)
    account_id = Column(Integer, ForeignKey('login_account.account_id', ondelete='CASCADE'), comment='账号ID')
    access_type = Column(String(20), comment='访问类型: view, download')
    ip_address = Column(String(50), comment='IP地址')
    user_agent = Column(String(500), comment='用户代理')
    access_time = Column(DateTime, server_default=func.now(), comment='访问时间')

    # 关系
    document = relationship("KnowledgeDocument", back_populates="access_logs")

    # 索引
    __table_args__ = (
        Index('idx_knowledge_access_log_doc', 'doc_id'),
        Index('idx_knowledge_access_log_account', 'account_id'),
    )

    def __repr__(self):
        return f"<KnowledgeAccessLog(doc_id={self.doc_id}, access_type={self.access_type})>"


class KnowledgeConfig(Base):
    """知识库配置表"""
    __tablename__ = "knowledge_config"

    config_id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False, comment='配置键')
    config_value = Column(Text, comment='配置值')
    config_description = Column(String(200), comment='配置说明')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

    # 索引
    __table_args__ = (
        Index('idx_knowledge_config_key', 'config_key'),
    )

    def __repr__(self):
        return f"<KnowledgeConfig(config_key={self.config_key})>"

# 注意: PromptConfig 已移动到 prompt.py，此处不再重复定义
