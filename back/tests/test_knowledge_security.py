"""知识库安全增强与AI摘要测试"""
import pytest
import hashlib
import uuid
from unittest.mock import AsyncMock, patch

from app.api.auth import get_current_user
from app.api.files import _extract_document_id, _extract_report_id
from app.core.database import get_db
from app.core.security import get_password_hash
from app.api.knowledge import (
    validate_mime_type,
    _check_document_duplicate,
    ALLOWED_MIME_MAP,
    ALLOWED_EXTENSIONS,
)
from app.api.knowledge_preview import _build_direct_preview_url
from app.models.user import LoginAccount
from app.models.knowledge import KnowledgeDocument
from app.services.storage_service import LocalStorageBackend


class TestMimeValidation:
    """MIME 类型验证测试"""

    def test_valid_pdf_mime(self):
        assert validate_mime_type("report.pdf", "application/pdf") is True

    def test_valid_docx_mime(self):
        assert validate_mime_type("report.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document") is True

    def test_valid_image_mime(self):
        assert validate_mime_type("photo.jpg", "image/jpeg") is True
        assert validate_mime_type("photo.png", "image/png") is True

    def test_mismatched_mime_rejected(self):
        assert validate_mime_type("report.pdf", "text/html") is False
        assert validate_mime_type("report.pdf", "application/javascript") is False

    def test_mismatched_exe_as_pdf(self):
        assert validate_mime_type("report.pdf", "application/octet-stream") is False

    def test_unknown_extension_passes(self):
        """扩展名不在映射表中时放行（由 allowed_file 兜底）"""
        assert validate_mime_type("file.xyz", "application/octet-stream") is True

    def test_empty_content_type(self):
        assert validate_mime_type("report.pdf", "") is False
        assert validate_mime_type("report.pdf", None) is False

    def test_mime_with_charset(self):
        """content_type 含 charset 参数时正确解析"""
        assert validate_mime_type("report.txt", "text/plain; charset=utf-8") is True

    def test_mime_map_covers_all_extensions(self):
        """ALLOWED_MIME_MAP 覆盖所有 ALLOWED_EXTENSIONS"""
        assert ALLOWED_EXTENSIONS == set(ALLOWED_MIME_MAP.keys())


class TestPreviewUrl:
    """预览器内层请求必须保持同源并正确编码 token。"""

    def test_direct_url_without_token_is_relative(self):
        assert _build_direct_preview_url(None) == "?direct=true"

    def test_direct_url_encodes_token_without_host(self):
        token = "header+payload/signature=="
        assert _build_direct_preview_url(token) == (
            "?direct=true&token=header%2Bpayload%2Fsignature%3D%3D"
        )


class TestDuplicateCheck:
    """重复文件校验测试"""

    @pytest.mark.asyncio
    async def test_duplicate_detected(self, db_session, test_user):
        """相同 account_id + file_hash 检测为重复"""
        file_hash = hashlib.sha256(b"test content").hexdigest()
        doc = KnowledgeDocument(
            doc_name="existing.txt",
            file_path="knowledge/test.txt",
            file_name="existing.txt",
            file_size=100,
            file_type="txt",
            file_hash=file_hash,
            account_id=test_user.account_id,
        )
        db_session.add(doc)
        await db_session.commit()

        result = await _check_document_duplicate(db_session, test_user.account_id, file_hash)
        assert result is not None
        assert result.doc_name == "existing.txt"

    @pytest.mark.asyncio
    async def test_different_content_not_duplicate(self, db_session, test_user):
        """不同 file_hash 不视为重复"""
        file_hash1 = hashlib.sha256(b"content A").hexdigest()
        file_hash2 = hashlib.sha256(b"content B").hexdigest()
        doc = KnowledgeDocument(
            doc_name="file_a.txt",
            file_path="knowledge/file_a.txt",
            file_name="file_a.txt",
            file_size=100,
            file_type="txt",
            file_hash=file_hash1,
            account_id=test_user.account_id,
        )
        db_session.add(doc)
        await db_session.commit()

        result = await _check_document_duplicate(db_session, test_user.account_id, file_hash2)
        assert result is None

    @pytest.mark.asyncio
    async def test_different_account_same_hash_not_duplicate(self, db_session, test_user):
        """不同 account_id 相同 file_hash 不视为重复"""
        file_hash = hashlib.sha256(b"shared content").hexdigest()
        # 直接用函数查询，无需插入跨账户记录（FK 约束不允许虚构 account_id）
        result = await _check_document_duplicate(db_session, test_user.account_id, file_hash)
        assert result is None


class TestUploadSecurityIntegration:
    """上传安全集成测试"""

    @pytest.mark.asyncio
    @patch('app.services.knowledge_summary_service.generate_knowledge_summary')
    async def test_upload_stores_sha256_hash(self, mock_task, client, test_user, auth_headers, db_session):
        """上传文件后 file_hash 存储 SHA-256 值"""
        content = b"Hello, knowledge base!"
        expected_hash = hashlib.sha256(content).hexdigest()

        response = await client.post(
            "/api/v1/knowledge/documents",
            headers=auth_headers,
            files={"file": ("test.txt", content, "text/plain")},
            data={"doc_name": "测试文档"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary_status"] == "pending"

        # 验证 DB 中 file_hash
        from sqlalchemy import select
        result = await db_session.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.doc_id == data["doc_id"])
        )
        doc = result.scalar_one()
        assert doc.file_hash == expected_hash

    @pytest.mark.asyncio
    @patch('app.services.knowledge_summary_service.generate_knowledge_summary')
    async def test_duplicate_upload_returns_409(self, mock_task, client, test_user, auth_headers):
        """重复文件上传返回 409"""
        content = b"Duplicate content test"

        # 第一次上传
        resp1 = await client.post(
            "/api/v1/knowledge/documents",
            headers=auth_headers,
            files={"file": ("dup.txt", content, "text/plain")},
            data={"doc_name": "第一次"},
        )
        assert resp1.status_code == 200

        # 第二次上传相同内容
        resp2 = await client.post(
            "/api/v1/knowledge/documents",
            headers=auth_headers,
            files={"file": ("dup_again.txt", content, "text/plain")},
            data={"doc_name": "第二次"},
        )
        assert resp2.status_code == 409
        assert "已存在" in resp2.json()["detail"]

    @pytest.mark.asyncio
    async def test_mime_mismatch_returns_400(self, client, test_user, auth_headers):
        """MIME 类型不匹配返回 400"""
        response = await client.post(
            "/api/v1/knowledge/documents",
            headers=auth_headers,
            files={"file": ("report.pdf", b"not really a pdf", "text/html")},
            data={"doc_name": "伪装文件"},
        )
        assert response.status_code == 400
        assert "MIME" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch('app.services.knowledge_summary_service.generate_knowledge_summary')
    async def test_image_upload_null_summary_status(self, mock_task, client, test_user, auth_headers):
        """图片上传后 summary_status 为 null"""
        # 创建一个最小有效 PNG
        png_data = (
            b'\x89PNG\r\n\x1a\n'  # PNG signature
            + b'\x00' * 100  # dummy data
        )
        response = await client.post(
            "/api/v1/knowledge/documents",
            headers=auth_headers,
            files={"file": ("test.png", png_data, "image/png")},
            data={"doc_name": "图片文档"},
        )
        assert response.status_code == 200
        assert response.json()["summary_status"] is None

    @pytest.mark.asyncio
    @patch('app.services.knowledge_summary_service.generate_knowledge_summary')
    async def test_download_has_nosniff_header(self, mock_task, client, test_user, auth_headers, db_session):
        """下载响应含 X-Content-Type-Options: nosniff"""
        # 先上传一个文件
        content = b"download test content"
        upload_resp = await client.post(
            "/api/v1/knowledge/documents",
            headers=auth_headers,
            files={"file": ("download.txt", content, "text/plain")},
            data={"doc_name": "下载测试"},
        )
        doc_id = upload_resp.json()["doc_id"]

        # 下载
        download_resp = await client.get(
            f"/api/v1/knowledge/documents/{doc_id}/download",
            headers=auth_headers,
        )
        assert download_resp.status_code == 200
        assert download_resp.headers.get("x-content-type-options") == "nosniff"


class TestFileServiceKnowledgeAuthorization:
    """文件服务知识库文档授权测试"""

    @pytest.mark.asyncio
    async def test_documents_bucket_rejects_cross_account_access(
        self, client, test_user, db_session
    ):
        """`/files/documents/*` 不能被其他登录用户跨账号读取"""
        from app.main import app

        owner = LoginAccount(
            username=f"knowledge_owner_{uuid.uuid4().hex[:8]}",
            password=get_password_hash("ownerpass123"),
            account_name="知识库所有者",
            status="active",
        )
        db_session.add(owner)
        await db_session.commit()
        await db_session.refresh(owner)

        doc = KnowledgeDocument(
            doc_name="private.txt",
            file_path="documents/123.txt",
            file_name="private.txt",
            file_size=7,
            file_type="txt",
            mime_type="text/plain",
            file_hash=hashlib.sha256(b"private").hexdigest(),
            account_id=owner.account_id,
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        app.dependency_overrides[get_current_user] = lambda: test_user
        try:
            response = await client.get(f"/api/v1/files/documents/{doc.doc_id}.txt")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_documents_bucket_allows_owner(
        self, client, test_user, db_session, tmp_path, monkeypatch
    ):
        """文档所有者可以通过文件服务读取自己的 documents bucket 文件"""
        from app.main import app
        from app.services import storage_service

        monkeypatch.setattr("app.core.config.settings.STORAGE_PATH", str(tmp_path))
        storage_service._storage_service = None

        doc = KnowledgeDocument(
            doc_name="owned.txt",
            file_path="documents/1.txt",
            file_name="owned.txt",
            file_size=5,
            file_type="txt",
            mime_type="text/plain",
            file_hash=hashlib.sha256(b"owned").hexdigest(),
            account_id=test_user.account_id,
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        try:
            storage = storage_service.get_storage_service()
            await storage._backend.save("documents", f"{doc.doc_id}.txt", b"owned")

            app.dependency_overrides[get_current_user] = lambda: test_user
            response = await client.get(f"/api/v1/files/documents/{doc.doc_id}.txt")

            assert response.status_code == 200
            assert response.content == b"owned"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            storage_service._storage_service = None


class TestFileServicePathTraversal:
    """文件 key 必须与被鉴权资源保持一一对应。"""

    @pytest.mark.parametrize(
        ("bucket", "key"),
        [
            ("images", "12/../13.jpg"),
            ("thumbnails", "12/../13_thumb.jpg"),
            ("pathology", "12/../13.png"),
        ],
    )
    def test_report_key_rejects_path_segments(self, bucket, key):
        assert _extract_report_id(bucket, key) is None

    def test_document_key_rejects_path_segments(self):
        assert _extract_document_id("12/../13.pdf") is None

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/files/images/12/%2e%2e/13.jpg",
            "/api/v1/files/thumbnails/12/%2e%2e/13_thumb.jpg",
            "/api/v1/files/pathology/12/%2e%2e/13.png",
            "/api/v1/files/documents/12/%2e%2e/13.pdf",
        ],
    )
    @pytest.mark.asyncio
    async def test_encoded_traversal_is_rejected_before_database_access(self, client, path):
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: LoginAccount(account_id=12)
        db = AsyncMock()

        async def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        try:
            response = await client.get(path)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 400
        db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_storage_rejects_key_outside_bucket(self, tmp_path):
        backend = LocalStorageBackend(str(tmp_path))

        with pytest.raises(ValueError, match="路径越界"):
            await backend.read("documents", "12/../13.pdf")

        with pytest.raises(ValueError, match="路径越界"):
            await backend.read("documents", "C:13.pdf")

        with pytest.raises(ValueError, match="路径越界"):
            await backend.read("documents", r"12\..\13.pdf")

    @pytest.mark.asyncio
    async def test_storage_keeps_valid_key_inside_bucket(self, tmp_path):
        backend = LocalStorageBackend(str(tmp_path))

        await backend.save("documents", "12.pdf", b"owned")

        assert await backend.read("documents", "12.pdf") == b"owned"
