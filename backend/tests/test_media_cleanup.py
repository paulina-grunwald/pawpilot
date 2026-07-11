from __future__ import annotations

import io
import uuid
from typing import IO, Any, cast

import pytest
from botocore.exceptions import ClientError

from app.media.cleanup import delete_media_quietly, delete_owner_dir_quietly
from app.media.storage import S3MediaStorage, StoredFile

JPEG_HEADER = b"\xff\xd8\xff\xe0"


class RecordingMediaStorage:
    """Minimal MediaStorage stub that records cleanup calls and can be told to
    raise, so we can assert the best-effort helpers swallow failures."""

    def __init__(self, *, raises: bool) -> None:
        self._raises = raises
        self.delete_calls: list[str | None] = []
        self.delete_owner_dir_calls: list[tuple[str, uuid.UUID]] = []

    async def save(
        self,
        namespace: str,
        subject_id: uuid.UUID,
        content_type: str,
        fileobj: IO[bytes],
    ) -> StoredFile:
        raise NotImplementedError

    async def read(self, relative_path: str) -> bytes | None:
        raise NotImplementedError

    async def delete(self, relative_path: str | None) -> None:
        self.delete_calls.append(relative_path)
        if self._raises:
            raise RuntimeError("object store unavailable")

    async def delete_owner_dir(self, namespace: str, subject_id: uuid.UUID) -> None:
        self.delete_owner_dir_calls.append((namespace, subject_id))
        if self._raises:
            raise RuntimeError("object store unavailable")


async def test_delete_media_quietly_skips_empty_path() -> None:
    media = RecordingMediaStorage(raises=True)
    await delete_media_quietly(media, None)
    await delete_media_quietly(media, "")
    assert media.delete_calls == []


async def test_delete_media_quietly_forwards_real_path() -> None:
    media = RecordingMediaStorage(raises=False)
    await delete_media_quietly(media, "pets/1/photo.jpg")
    assert media.delete_calls == ["pets/1/photo.jpg"]


async def test_delete_media_quietly_swallows_delete_failure() -> None:
    media = RecordingMediaStorage(raises=True)
    await delete_media_quietly(media, "pets/1/photo.jpg")
    assert media.delete_calls == ["pets/1/photo.jpg"]


async def test_delete_owner_dir_quietly_swallows_failure() -> None:
    media = RecordingMediaStorage(raises=True)
    owner_id = uuid.uuid4()
    await delete_owner_dir_quietly(media, "pets", owner_id)
    assert media.delete_owner_dir_calls == [("pets", owner_id)]


class FakeS3Client:
    """Stub S3 client for bucket-provisioning unit tests (no network)."""

    def __init__(self, *, head_bucket_status: int) -> None:
        self._head_bucket_status = head_bucket_status
        self.created = False
        self.put_object_calls: list[dict[str, object]] = []

    def head_bucket(self, *, Bucket: str) -> dict[str, object]:
        if self._head_bucket_status == 200:
            return {}
        error_response: Any = {
            "ResponseMetadata": {"HTTPStatusCode": self._head_bucket_status},
            "Error": {"Code": str(self._head_bucket_status)},
        }
        raise ClientError(error_response, "HeadBucket")

    def create_bucket(self, *, Bucket: str) -> dict[str, object]:
        self.created = True
        return {}

    def put_object(self, **kwargs: object) -> dict[str, object]:
        self.put_object_calls.append(kwargs)
        return {}


def _s3_storage(client: FakeS3Client) -> S3MediaStorage:
    return S3MediaStorage(client=cast("object", client), bucket="pawpilot-media")  # type: ignore[arg-type]


async def _save_jpeg(storage: S3MediaStorage) -> None:
    await storage.save(
        namespace="pets",
        subject_id=uuid.uuid4(),
        content_type="image/jpeg",
        fileobj=io.BytesIO(JPEG_HEADER),
    )


async def test_head_bucket_403_does_not_block_operations() -> None:
    client = FakeS3Client(head_bucket_status=403)
    await _save_jpeg(_s3_storage(client))
    assert client.created is False
    assert len(client.put_object_calls) == 1


async def test_head_bucket_404_creates_bucket() -> None:
    client = FakeS3Client(head_bucket_status=404)
    await _save_jpeg(_s3_storage(client))
    assert client.created is True
    assert len(client.put_object_calls) == 1


async def test_head_bucket_success_skips_create() -> None:
    client = FakeS3Client(head_bucket_status=200)
    await _save_jpeg(_s3_storage(client))
    assert client.created is False
    assert len(client.put_object_calls) == 1


@pytest.mark.parametrize("status", [200, 403, 404])
async def test_bucket_check_runs_once_then_caches(status: int) -> None:
    client = FakeS3Client(head_bucket_status=status)
    storage = _s3_storage(client)
    await _save_jpeg(storage)
    await _save_jpeg(storage)
    assert len(client.put_object_calls) == 2
