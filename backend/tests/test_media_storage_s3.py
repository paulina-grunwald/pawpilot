from __future__ import annotations

import io
import time
import uuid
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from testcontainers.core.container import DockerContainer

from app.media.storage import (
    MAX_BYTES,
    PayloadTooLargeError,
    S3MediaStorage,
    UnsupportedMediaTypeError,
)

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

JPEG_HEADER = b"\xff\xd8\xff\xe0"
BUCKET = "pawpilot-media-test"
ACCESS_KEY = "minio-test-user"
SECRET_KEY = "minio-test-password"


def _jpeg_bytes(trailing: bytes = b"") -> bytes:
    return JPEG_HEADER + trailing


@pytest.fixture(scope="session")
def minio_endpoint() -> Iterator[str]:
    container = (
        DockerContainer("minio/minio:latest")
        .with_env("MINIO_ROOT_USER", ACCESS_KEY)
        .with_env("MINIO_ROOT_PASSWORD", SECRET_KEY)
        .with_exposed_ports(9000)
        .with_command("server /data")
    )
    with container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(9000)
        yield f"http://{host}:{port}"


def _make_client(endpoint: str) -> S3Client:
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name="us-east-1",
        config=Config(
            s3={"addressing_style": "path"},
            retries={"max_attempts": 2},
            connect_timeout=5,
            read_timeout=10,
        ),
    )


@pytest.fixture(scope="session")
def s3_client(minio_endpoint: str) -> S3Client:
    client = _make_client(minio_endpoint)
    deadline = time.monotonic() + 30
    while True:
        try:
            client.list_buckets()
            return client
        except (ClientError, BotoCoreError):
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)


@pytest.fixture
def s3_storage(s3_client: S3Client) -> S3MediaStorage:
    return S3MediaStorage(client=s3_client, bucket=BUCKET)


async def test_save_creates_bucket_and_roundtrips_payload(s3_storage: S3MediaStorage) -> None:
    owner_id = uuid.uuid4()
    payload = _jpeg_bytes(b"-body")

    stored = await s3_storage.save(
        namespace="journal",
        subject_id=owner_id,
        content_type="image/jpeg",
        fileobj=io.BytesIO(payload),
    )

    assert stored.relative_path.startswith(f"journal/{owner_id}/")
    assert stored.relative_path.endswith(".jpg")
    assert await s3_storage.read(stored.relative_path) == payload


async def test_read_returns_none_for_missing_key(s3_storage: S3MediaStorage) -> None:
    assert await s3_storage.read("journal/nonexistent/missing.jpg") is None


async def test_save_rejects_unsupported_mime_type(s3_storage: S3MediaStorage) -> None:
    with pytest.raises(UnsupportedMediaTypeError):
        await s3_storage.save(
            namespace="pets",
            subject_id=uuid.uuid4(),
            content_type="text/plain",
            fileobj=io.BytesIO(b"hello"),
        )


async def test_save_rejects_signature_mismatch(s3_storage: S3MediaStorage) -> None:
    with pytest.raises(UnsupportedMediaTypeError):
        await s3_storage.save(
            namespace="pets",
            subject_id=uuid.uuid4(),
            content_type="image/jpeg",
            fileobj=io.BytesIO(b"not-an-image"),
        )


async def test_save_rejects_payload_exceeding_max_bytes(s3_storage: S3MediaStorage) -> None:
    with pytest.raises(PayloadTooLargeError):
        await s3_storage.save(
            namespace="pets",
            subject_id=uuid.uuid4(),
            content_type="image/jpeg",
            fileobj=io.BytesIO(_jpeg_bytes(b"x" * (MAX_BYTES + 1))),
        )


async def test_delete_removes_object_and_is_idempotent(s3_storage: S3MediaStorage) -> None:
    stored = await s3_storage.save(
        namespace="pets",
        subject_id=uuid.uuid4(),
        content_type="image/jpeg",
        fileobj=io.BytesIO(_jpeg_bytes()),
    )

    await s3_storage.delete(stored.relative_path)
    assert await s3_storage.read(stored.relative_path) is None

    await s3_storage.delete(stored.relative_path)
    await s3_storage.delete(None)


async def test_delete_owner_dir_removes_only_that_owners_objects(
    s3_storage: S3MediaStorage,
) -> None:
    wiped_owner = uuid.uuid4()
    kept_owner = uuid.uuid4()
    wiped_paths = []
    for _ in range(3):
        stored = await s3_storage.save(
            namespace="journal",
            subject_id=wiped_owner,
            content_type="image/jpeg",
            fileobj=io.BytesIO(_jpeg_bytes()),
        )
        wiped_paths.append(stored.relative_path)
    kept = await s3_storage.save(
        namespace="journal",
        subject_id=kept_owner,
        content_type="image/jpeg",
        fileobj=io.BytesIO(_jpeg_bytes(b"keep")),
    )

    await s3_storage.delete_owner_dir("journal", wiped_owner)

    for path in wiped_paths:
        assert await s3_storage.read(path) is None
    assert await s3_storage.read(kept.relative_path) == _jpeg_bytes(b"keep")
