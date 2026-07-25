"""知识库文档摘要生成

为文档生成 AI 摘要，结果写入 knowledge_document.summary。
复用 office_converter 提取文本，不重复引入解析依赖。
"""
import re
import logging

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

# 同步数据库连接
_sync_engine = None
_SyncSessionLocal = None


def _get_sync_session():
    global _sync_engine, _SyncSessionLocal
    if _sync_engine is None:
        db_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
        if not db_url.startswith("postgresql"):
            db_url = (
                f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
                f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
            )
        _sync_engine = create_engine(db_url)
        _SyncSessionLocal = sessionmaker(bind=_sync_engine)
    return _SyncSessionLocal()


# 支持摘要生成的文件类型
SUMMARY_SUPPORTED_TYPES = {'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

# LLM prompt
SUMMARY_SYSTEM_PROMPT = (
    "你是一个文档摘要助手。请为以下文档内容生成一段简洁的中文摘要，"
    "概括文档的核心主题和关键信息。摘要不超过500字。"
    "只输出摘要内容，不要加标题或前缀。"
)

MAX_INPUT_CHARS = 300_000
MAX_SUMMARY_CHARS = 500


def _strip_html_tags(html: str) -> str:
    """去除 HTML 标签，保留纯文本"""
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&[a-zA-Z]+;', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _extract_text(file_path: str, file_type: str) -> str:
    """提取文档文本内容

    txt/md 直接读取；其他格式复用 office_converter 转 HTML 后去标签。
    """
    if file_type in ('txt', 'md'):
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    # 复用已有的 office_converter（内部处理 docx/xlsx/pptx/pdf 各格式）
    from app.utils.office_converter import office_converter

    if not office_converter.is_supported(file_type):
        raise ValueError(f"不支持的文件类型: {file_type}")

    success, html_content, error_msg = office_converter.convert_to_html(file_path, file_type)
    if not success or not html_content:
        raise ValueError(f"文档转换失败: {error_msg}")

    return _strip_html_tags(html_content)


async def generate_knowledge_summary(doc_id: int, file_path: str, file_type: str):
    """为知识库文档生成 AI 摘要

    Args:
        doc_id: 文档 ID
        file_path: 文件完整路径（已解析的绝对路径）
        file_type: 文件扩展名
    """
    from app.models.knowledge import KnowledgeDocument

    db = _get_sync_session()
    try:
        result = db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.doc_id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            logger.warning(f"摘要任务：文档不存在 doc_id={doc_id}")
            return

        # 提取文本
        try:
            text = _extract_text(file_path, file_type)
        except Exception as e:
            logger.error(f"摘要任务：文本提取失败 doc_id={doc_id}, error={e}")
            doc.summary_status = 'failed'
            db.commit()
            return

        if not text or not text.strip():
            logger.info(f"摘要任务：文档无文本内容 doc_id={doc_id}")
            doc.summary_status = 'failed'
            db.commit()
            return

        # 截断
        text = text[:MAX_INPUT_CHARS]

        # 调用 LLM 生成摘要
        try:
            from app.services.llm_service import LLMService
            llm = LLMService()
            summary = await llm.chat(
                system_prompt=SUMMARY_SYSTEM_PROMPT,
                user_message=text,
                max_tokens=1024,
            )
        except Exception as e:
            logger.error(f"摘要任务：LLM 调用失败 doc_id={doc_id}, error={e}")
            doc.summary_status = 'failed'
            db.commit()
            return

        # 截取并保存
        doc.summary = (summary or '')[:MAX_SUMMARY_CHARS]
        doc.summary_status = 'completed'
        db.commit()
        logger.info(f"摘要任务：生成成功 doc_id={doc_id}, length={len(doc.summary)}")

    except Exception as e:
        logger.error(f"摘要任务：未知错误 doc_id={doc_id}, error={e}")
        try:
            doc.summary_status = 'failed'
            db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()
