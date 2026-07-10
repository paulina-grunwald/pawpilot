from __future__ import annotations

import shutil
import uuid
from functools import partial
from pathlib import Path
from typing import IO, TYPE_CHECKING, Literal, Protocol

from anyio import to_thread
from botocore.exceptions import ClientError
from pydantic import BaseModel

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

MediaMimeType = Literal["image/png", "image/jpeg", "image/webp"]

MIME_EXTENSIONS: dict[MediaMimeType, str] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}

MIME_BY_EXTENSION: dict[str, str] = {
    f".{extension}": mime_type for mime_type, extension in MIME_EXTENSIONS.items()
}

MAX_BYTES = 5 * 1024 * 1024
_SIGNATURE_PEEK_BYTES = 12


def _matches_signature(content_type: MediaMimeType, header: bytes) -> bool:
    if content_type == "image/png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/jpeg":
        return header.startswith(b"\xff\xd8\xff")
    if content_type == "image/webp":
        return len(header) >= 12 and header[0:4] == b"RIFF" and header[8:12] == b"WEBP"
    return False


class StoredFile(BaseModel):
    relative_path: str


class UnsupportedMediaTypeError(ValueError):
    pass


class PayloadTooLargeError(ValueError):
    pass


def _read_validated_upload(content_type: str, fileobj: IO[bytes]) -> tuple[bytes, str]:
    """Validate declared MIME type, magic bytes, and size cap; return the
    payload and its canonical file extension."""
    if content_type not in MIME_EXTENSIONS:
        raise UnsupportedMediaTypeError(
            f"unsupported media type: {content_type!r}",
        )
    validated_content_type: MediaMimeType = content_type
    extension = MIME_EXTENSIONS[validated_content_type]

    signature = fileobj.read(_SIGNATURE_PEEK_BYTES)
    if not _matches_signature(validated_content_type, signature):
        raise UnsupportedMediaTypeError(
            f"file contents do not match declared media type {content_type!r}",
        )

    chunks = [signature]
    bytes_read = len(signature)
    while True:
        chunk = fileobj.read(64 * 1024)
        if not chunk:
            break
        bytes_read += len(chunk)
        if bytes_read > MAX_BYTES:
            raise PayloadTooLargeError(
                f"file exceeds maximum size of {MAX_BYTES} bytes",
            )
        chunks.append(chunk)
    return b"".join(chunks), extension


def _object_key(namespace: str, subject_id: uuid.UUID, extension: str) -> str:
    return f"{namespace}/{subject_id}/{uuid.uuid4().hex}.{extension}"


class MediaStorage(Protocol):
    async def save(
        self,
        namespace: str,
        subject_id: uuid.UUID,
        content_type: str,
        fileobj: IO[bytes],
    ) -> StoredFile: ...

    async def read(self, relative_path: str) -> bytes | None: ...

    async def delete(self, relative_path: str | None) -> None: ...

    async def delete_owner_dir(self, namespace: str, subject_id: uuid.UUID) -> None: ...


class LocalMediaStorage:
    def __init__(self, media_root: Path) -> None:
        self.media_root = media_root

    def _namespace_dir(self, namespace: str, subject_id: uuid.UUID) -> Path:
        return self.media_root / namespace / str(subject_id)

    def _contained_path(self, relative_path: str) -> Path | None:
        """Resolve ``relative_path`` under the media root, or ``None`` if it
        would escape the root (path-traversal guard). Existence is not checked.
        """
        media_root_resolved = self.media_root.resolve()
        absolute_path = (self.media_root / relative_path).resolve()
        if media_root_resolved not in absolute_path.parents:
            return None
        return absolute_path

    async def save(
        self,
        namespace: str,
        subject_id: uuid.UUID,
        content_type: str,
        fileobj: IO[bytes],
    ) -> StoredFile:
        payload, extension = _read_validated_upload(content_type, fileobj)
        relative_path = _object_key(namespace, subject_id, extension)
        absolute_path = self.media_root / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_bytes(payload)
        return StoredFile(relative_path=relative_path)

    async def read(self, relative_path: str) -> bytes | None:
        absolute_path = self._contained_path(relative_path)
        if absolute_path is None or not absolute_path.is_file():
            return None
        return absolute_path.read_bytes()

    async def delete(self, relative_path: str | None) -> None:
        if not relative_path:
            return
        absolute_path = self._contained_path(relative_path)
        if absolute_path is None:
            return
        absolute_path.unlink(missing_ok=True)

    async def delete_owner_dir(self, namespace: str, subject_id: uuid.UUID) -> None:
        target = self._namespace_dir(namespace, subject_id)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)


class S3MediaStorage:
    """S3-compatible object storage (MinIO, R2, S3). Boto3 is synchronous, so
    every call is pushed to a worker thread to keep the event loop free."""

    def __init__(self, client: S3Client, bucket: str) -> None:
        self._client = client
        self._bucket = bucket
        self._bucket_verified = False

    def _ensure_bucket_sync(self) -> None:
        if self._bucket_verified:
            return
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError as error:
            status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status == 404:
                self._client.create_bucket(Bucket=self._bucket)
            # A non-404 status (e.g. 403 from an object-scoped credential that
            # may PutObject/GetObject but not HeadBucket) does not mean the
            # bucket is unusable: assume it exists and let the actual object
            # operation surface any genuine permission failure.
        self._bucket_verified = True

    def _save_sync(self, key: str, payload: bytes, content_type: str) -> None:
        self._ensure_bucket_sync()
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=payload,
            ContentType=content_type,
        )

    def _read_sync(self, key: str) -> bytes | None:
        self._ensure_bucket_sync()
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in {"NoSuchKey", "404"}:
                return None
            raise
        return response["Body"].read()

    def _delete_sync(self, key: str) -> None:
        self._ensure_bucket_sync()
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def _delete_prefix_sync(self, prefix: str) -> None:
        self._ensure_bucket_sync()
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            contents = page.get("Contents", [])
            if not contents:
                continue
            self._client.delete_objects(
                Bucket=self._bucket,
                Delete={"Objects": [{"Key": item["Key"]} for item in contents if "Key" in item]},
            )

    async def save(
        self,
        namespace: str,
        subject_id: uuid.UUID,
        content_type: str,
        fileobj: IO[bytes],
    ) -> StoredFile:
        payload, extension = _read_validated_upload(content_type, fileobj)
        key = _object_key(namespace, subject_id, extension)
        await to_thread.run_sync(partial(self._save_sync, key, payload, content_type))
        return StoredFile(relative_path=key)

    async def read(self, relative_path: str) -> bytes | None:
        return await to_thread.run_sync(partial(self._read_sync, relative_path))

    async def delete(self, relative_path: str | None) -> None:
        if not relative_path:
            return
        await to_thread.run_sync(partial(self._delete_sync, relative_path))

    async def delete_owner_dir(self, namespace: str, subject_id: uuid.UUID) -> None:
        await to_thread.run_sync(partial(self._delete_prefix_sync, f"{namespace}/{subject_id}/"))
