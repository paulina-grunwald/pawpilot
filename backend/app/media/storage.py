from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import IO, Literal

from pydantic import BaseModel

MediaMimeType = Literal["image/png", "image/jpeg", "image/webp"]

MIME_EXTENSIONS: dict[MediaMimeType, str] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
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
    absolute_path: Path


class UnsupportedMediaTypeError(ValueError):
    pass


class PayloadTooLargeError(ValueError):
    pass


class MediaStorage:
    def __init__(self, media_root: Path) -> None:
        self.media_root = media_root

    def _namespace_dir(self, namespace: str, owner_id: uuid.UUID) -> Path:
        return self.media_root / namespace / str(owner_id)

    def save(
        self,
        namespace: str,
        owner_id: uuid.UUID,
        content_type: str,
        fileobj: IO[bytes],
    ) -> StoredFile:
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

        target_dir = self._namespace_dir(namespace, owner_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        new_name = f"{uuid.uuid4().hex}.{extension}"
        absolute_path = target_dir / new_name

        bytes_written = 0
        with absolute_path.open("wb") as destination:
            destination.write(signature)
            bytes_written += len(signature)
            while True:
                chunk = fileobj.read(64 * 1024)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > MAX_BYTES:
                    destination.close()
                    absolute_path.unlink(missing_ok=True)
                    raise PayloadTooLargeError(
                        f"file exceeds maximum size of {MAX_BYTES} bytes",
                    )
                destination.write(chunk)

        relative_path = f"{namespace}/{owner_id}/{new_name}"
        return StoredFile(relative_path=relative_path, absolute_path=absolute_path)

    def delete(self, relative_path: str | None) -> None:
        if not relative_path:
            return
        media_root_resolved = self.media_root.resolve()
        absolute_path = (self.media_root / relative_path).resolve()
        if media_root_resolved not in absolute_path.parents:
            return
        try:
            absolute_path.unlink()
        except FileNotFoundError:
            return

    def resolve_within_root(self, relative_path: str) -> Path | None:
        """Resolve a stored relative path to an existing file inside the media
        root, or ``None`` if it would escape the root or doesn't exist.

        Path-traversal guard mirrors ``delete`` — callers that serve files to
        clients must never follow a ``..`` outside the media root.
        """
        media_root_resolved = self.media_root.resolve()
        absolute_path = (self.media_root / relative_path).resolve()
        if media_root_resolved not in absolute_path.parents:
            return None
        if not absolute_path.is_file():
            return None
        return absolute_path

    def delete_owner_dir(self, namespace: str, owner_id: uuid.UUID) -> None:
        target = self._namespace_dir(namespace, owner_id)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
