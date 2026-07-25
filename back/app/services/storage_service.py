"""文件存储服务抽象层 - 支持本地文件系统和未来MinIO"""
import os
import shutil
import logging
from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Optional, BinaryIO
from fastapi import UploadFile

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """存储后端抽象基类"""

    @abstractmethod
    async def save(self, bucket: str, key: str, data: bytes) -> str:
        """保存文件，返回存储路径/URL"""
        ...

    @abstractmethod
    async def read(self, bucket: str, key: str) -> Optional[bytes]:
        """读取文件内容"""
        ...

    @abstractmethod
    async def delete(self, bucket: str, key: str) -> bool:
        """删除文件，返回是否成功"""
        ...

    @abstractmethod
    async def exists(self, bucket: str, key: str) -> bool:
        """文件是否存在"""
        ...

    @abstractmethod
    async def get_url(self, bucket: str, key: str) -> str:
        """获取文件访问URL"""
        ...


class LocalStorageBackend(StorageBackend):
    """本地文件系统存储"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, bucket: str, key: str) -> Path:
        """解析安全路径，防止路径遍历"""
        base_path = self.base_path.resolve()
        bucket_key = Path(bucket)
        file_key = Path(key)
        bucket_views = (PurePosixPath(bucket), PureWindowsPath(bucket))
        file_views = (PurePosixPath(key), PureWindowsPath(key))
        if (
            bucket in {"", ".", ".."}
            or any(path.drive or path.is_absolute() or len(path.parts) != 1 for path in bucket_views)
        ):
            raise ValueError(f"非法 bucket: {bucket}")
        if (
            key in {"", ".", ".."}
            or any(path.drive or path.is_absolute() or ".." in path.parts for path in file_views)
        ):
            raise ValueError(f"路径越界: {key}")

        bucket_path = (base_path / bucket_key).resolve()
        try:
            bucket_path.relative_to(base_path)
        except ValueError:
            raise ValueError(f"非法 bucket: {bucket}")

        full_path = (bucket_path / file_key).resolve()
        try:
            full_path.relative_to(bucket_path)
        except ValueError:
            raise ValueError(f"路径越界: {key}")
        return full_path

    async def save(self, bucket: str, key: str, data: bytes) -> str:
        file_path = self._resolve_path(bucket, key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        logger.debug(f"文件已保存: {bucket}/{key}")
        return f"{bucket}/{key}"

    async def read(self, bucket: str, key: str) -> Optional[bytes]:
        file_path = self._resolve_path(bucket, key)
        if not file_path.exists():
            return None
        return file_path.read_bytes()

    async def delete(self, bucket: str, key: str) -> bool:
        file_path = self._resolve_path(bucket, key)
        if not file_path.exists():
            return False
        file_path.unlink()
        logger.debug(f"文件已删除: {bucket}/{key}")
        return True

    async def exists(self, bucket: str, key: str) -> bool:
        return self._resolve_path(bucket, key).exists()

    async def get_url(self, bucket: str, key: str) -> str:
        return f"/files/{bucket}/{key}"


class StorageService:
    """存储服务门面 - 提供统一的文件存储接口"""

    def __init__(self, backend: StorageBackend):
        self._backend = backend

    @classmethod
    def create(cls, backend_type: str = "local", **kwargs) -> "StorageService":
        """工厂方法：创建存储服务实例"""
        if backend_type == "local":
            base_path = kwargs.get("base_path", "storage")
            backend = LocalStorageBackend(base_path)
        else:
            raise ValueError(f"不支持的存储后端: {backend_type}")
        return cls(backend)

    async def save(self, bucket: str, key: str, data: bytes) -> str:
        """保存任意 bucket/key 文件。"""
        return await self._backend.save(bucket, key, data)

    async def read(self, bucket: str, key: str) -> Optional[bytes]:
        """读取任意 bucket/key 文件。"""
        return await self._backend.read(bucket, key)

    async def delete(self, bucket: str, key: str) -> bool:
        """删除任意 bucket/key 文件。"""
        return await self._backend.delete(bucket, key)

    async def exists(self, bucket: str, key: str) -> bool:
        """检查任意 bucket/key 文件是否存在。"""
        return await self._backend.exists(bucket, key)

    async def save_image(self, report_id: int, image_data: bytes, ext: str = "jpg") -> str:
        """保存报告的文件文件"""
        key = f"{report_id}.{ext}"
        return await self._backend.save("images", key, image_data)

    async def read_image(self, report_id: int, ext: str = "jpg") -> Optional[bytes]:
        """读取报告的文件文件"""
        key = f"{report_id}.{ext}"
        return await self._backend.read("images", key)

    async def delete_image(self, report_id: int, ext: str = "jpg") -> bool:
        """删除报告的文件文件"""
        key = f"{report_id}.{ext}"
        return await self._backend.delete("images", key)

    async def image_exists(self, report_id: int, ext: str = "jpg") -> bool:
        """检查图片文件是否存在"""
        key = f"{report_id}.{ext}"
        return await self._backend.exists("images", key)

    async def get_image_url(self, report_id: int, ext: str = "jpg") -> str:
        """获取图片访问URL"""
        key = f"{report_id}.{ext}"
        return await self._backend.get_url("images", key)

    async def save_thumbnail(self, report_id: int, thumbnail_data: bytes, ext: str = "jpg") -> str:
        """保存缩略图"""
        key = f"{report_id}_thumb.{ext}"
        return await self._backend.save("thumbnails", key, thumbnail_data)

    async def read_thumbnail(self, report_id: int, ext: str = "jpg") -> Optional[bytes]:
        """读取缩略图"""
        key = f"{report_id}_thumb.{ext}"
        return await self._backend.read("thumbnails", key)

    async def get_thumbnail_url(self, report_id: int, ext: str = "jpg") -> str:
        """获取缩略图访问URL"""
        key = f"{report_id}_thumb.{ext}"
        return await self._backend.get_url("thumbnails", key)

    async def save_pathology_image(self, report_id: int, image_data: bytes, ext: str = "jpg") -> str:
        """保存病理报告图片"""
        key = f"{report_id}.{ext}"
        return await self._backend.save("pathology", key, image_data)

    async def read_pathology_image(self, report_id: int, ext: str = "jpg") -> Optional[bytes]:
        """读取病理报告图片"""
        key = f"{report_id}.{ext}"
        return await self._backend.read("pathology", key)

    async def delete_pathology_image(self, report_id: int, ext: str = "jpg") -> bool:
        """删除病理报告图片"""
        key = f"{report_id}.{ext}"
        return await self._backend.delete("pathology", key)

    async def pathology_image_exists(self, report_id: int, ext: str = "jpg") -> bool:
        """检查病理报告图片是否存在"""
        key = f"{report_id}.{ext}"
        return await self._backend.exists("pathology", key)

    async def save_document(self, doc_id: int, data: bytes, filename: str) -> str:
        """保存知识库文档文件"""
        ext = Path(filename).suffix or ".bin"
        key = f"{doc_id}{ext}"
        return await self._backend.save("documents", key, data)

    async def read_document(self, doc_id: int, ext: str) -> Optional[bytes]:
        """读取知识库文档文件"""
        key = f"{doc_id}{ext}"
        return await self._backend.read("documents", key)

    async def delete_document(self, doc_id: int, ext: str) -> bool:
        """删除知识库文档文件"""
        key = f"{doc_id}{ext}"
        return await self._backend.delete("documents", key)

    async def document_exists(self, doc_id: int, ext: str) -> bool:
        """检查文档文件是否存在"""
        key = f"{doc_id}{ext}"
        return await self._backend.exists("documents", key)


# 全局单例
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """获取全局存储服务实例"""
    global _storage_service
    if _storage_service is None:
        from app.core.config import settings
        storage_type = getattr(settings, "STORAGE_TYPE", "local")
        storage_path = getattr(settings, "STORAGE_PATH", "storage")
        _storage_service = StorageService.create(
            backend_type=storage_type,
            base_path=storage_path
        )
    return _storage_service
