"""Tests for the file storage service."""

from __future__ import annotations

import os
import tempfile

import pytest

from app.services.file_storage import (
    LocalStorageBackend,
    create_file_storage,
)


# -------------------------------------------------------------------
# Local storage backend
# -------------------------------------------------------------------


@pytest.fixture
def local_storage(tmp_path):
    """Create a LocalStorageBackend using a temp directory."""
    return LocalStorageBackend(base_path=str(tmp_path))


@pytest.mark.asyncio
async def test_local_upload_and_download(local_storage: LocalStorageBackend):
    """Round-trip: upload then download returns identical content."""
    data = b"column1,column2\n1,2\n3,4"
    key = "datasets/test-123/data.csv"

    path = await local_storage.upload(key, data, "text/csv")
    assert path  # Returns a path

    downloaded = await local_storage.download(key)
    assert downloaded == data


@pytest.mark.asyncio
async def test_local_delete(local_storage: LocalStorageBackend):
    """Delete removes the file from disk."""
    key = "reports/report-1.html"
    await local_storage.upload(key, b"<html>Report</html>")

    await local_storage.delete(key)

    with pytest.raises(FileNotFoundError):
        await local_storage.download(key)


@pytest.mark.asyncio
async def test_local_delete_nonexistent(local_storage: LocalStorageBackend):
    """Deleting a non-existent file is a no-op."""
    await local_storage.delete("does/not/exist.csv")  # Should not raise


@pytest.mark.asyncio
async def test_local_get_url(local_storage: LocalStorageBackend):
    """get_url returns a valid path string."""
    url = local_storage.get_url("datasets/test/data.csv")
    assert "datasets" in url
    assert "data.csv" in url


@pytest.mark.asyncio
async def test_local_download_nonexistent(local_storage: LocalStorageBackend):
    """Downloading a non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        await local_storage.download("no/such/file.csv")


@pytest.mark.asyncio
async def test_local_nested_directories(local_storage: LocalStorageBackend):
    """Upload creates nested directories as needed."""
    key = "a/b/c/d/deep.txt"
    await local_storage.upload(key, b"deep content")
    result = await local_storage.download(key)
    assert result == b"deep content"


# -------------------------------------------------------------------
# Factory
# -------------------------------------------------------------------


def test_create_file_storage_local(tmp_path):
    """Factory creates LocalStorageBackend for backend='local'."""
    from unittest.mock import MagicMock

    settings = MagicMock()
    settings.storage_backend = "local"
    settings.storage_local_path = str(tmp_path / "uploads")

    backend = create_file_storage(settings)
    assert isinstance(backend, LocalStorageBackend)
