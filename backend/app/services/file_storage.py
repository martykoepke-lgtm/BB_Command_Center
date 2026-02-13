"""
File storage service — abstract interface with local and S3 backends.

Nexus Phase 5: Persists uploaded datasets and generated reports to
durable storage. Local filesystem for development, S3-compatible
storage (AWS S3, Supabase Storage, MinIO) for production.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class FileStorageBackend(ABC):
    """Abstract file storage interface."""

    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str = "") -> str:
        """
        Upload a file. Returns the storage path/URL.

        Args:
            key: Storage key (e.g., "datasets/{id}/data.csv")
            data: File content as bytes
            content_type: MIME type (e.g., "text/csv")

        Returns:
            The storage path or URL for later retrieval
        """

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download a file by key. Returns file content as bytes."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a file by key. No-op if file doesn't exist."""

    @abstractmethod
    def get_url(self, key: str) -> str:
        """Get a URL or path for the stored file."""


class LocalStorageBackend(FileStorageBackend):
    """
    Stores files on the local filesystem.

    Default backend for development. Files are stored under
    a configurable base directory (default: ./uploads).
    """

    def __init__(self, base_path: str = "./uploads") -> None:
        self._base = Path(base_path)
        self._base.mkdir(parents=True, exist_ok=True)
        logger.info("LocalStorageBackend initialized: %s", self._base.resolve())

    async def upload(self, key: str, data: bytes, content_type: str = "") -> str:
        path = self._base / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    async def download(self, key: str) -> bytes:
        path = self._base / key
        if not path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        return path.read_bytes()

    async def delete(self, key: str) -> None:
        path = self._base / key
        if path.exists():
            path.unlink()

    def get_url(self, key: str) -> str:
        return str(self._base / key)


class S3StorageBackend(FileStorageBackend):
    """
    Stores files in S3-compatible storage.

    Supports AWS S3, Supabase Storage, MinIO, and other S3-compatible services.
    Uses boto3 for S3 operations, run via asyncio.to_thread() to avoid blocking.
    """

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        access_key: str = "",
        secret_key: str = "",
        endpoint_url: str = "",
    ) -> None:
        self._bucket = bucket
        self._region = region
        self._endpoint_url = endpoint_url or None

        try:
            import boto3
            kwargs: dict = {
                "service_name": "s3",
                "region_name": region,
            }
            if access_key and secret_key:
                kwargs["aws_access_key_id"] = access_key
                kwargs["aws_secret_access_key"] = secret_key
            if self._endpoint_url:
                kwargs["endpoint_url"] = self._endpoint_url
            self._client = boto3.client(**kwargs)
            logger.info("S3StorageBackend initialized: bucket=%s region=%s", bucket, region)
        except ImportError:
            raise RuntimeError(
                "boto3 is required for S3 storage. Install it with: pip install boto3"
            )

    async def upload(self, key: str, data: bytes, content_type: str = "") -> str:
        import asyncio

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            **extra_args,
        )
        return key

    async def download(self, key: str) -> bytes:
        import asyncio

        response = await asyncio.to_thread(
            self._client.get_object,
            Bucket=self._bucket,
            Key=key,
        )
        return response["Body"].read()

    async def delete(self, key: str) -> None:
        import asyncio

        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self._bucket,
            Key=key,
        )

    def get_url(self, key: str) -> str:
        if self._endpoint_url:
            return f"{self._endpoint_url}/{self._bucket}/{key}"
        return f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{key}"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_file_storage(settings) -> FileStorageBackend:
    """
    Create a file storage backend based on settings.

    Settings fields used:
        storage_backend: "local" or "s3"
        storage_local_path: Directory for local storage
        s3_bucket, s3_region, s3_access_key, s3_secret_key, s3_endpoint_url
    """
    backend = getattr(settings, "storage_backend", "local")

    if backend == "s3":
        return S3StorageBackend(
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            endpoint_url=settings.s3_endpoint_url,
        )
    else:
        path = getattr(settings, "storage_local_path", "./uploads")
        return LocalStorageBackend(base_path=path)


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_file_storage: FileStorageBackend | None = None


def init_file_storage(settings) -> FileStorageBackend:
    """Create and store the global file storage singleton."""
    global _file_storage
    _file_storage = create_file_storage(settings)
    return _file_storage


def get_file_storage() -> FileStorageBackend:
    """FastAPI dependency: returns the global file storage."""
    if _file_storage is None:
        raise RuntimeError("FileStorage not initialized — app not started")
    return _file_storage
