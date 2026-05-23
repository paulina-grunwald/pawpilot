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
        extension = MIME_EXTENSIONS[content_type]

        target_dir = self._namespace_dir(namespace, owner_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        new_name = f"{uuid.uuid4().hex}.{extension}"
        absolute_path = target_dir / new_name

        bytes_written = 0
        with absolute_path.open("wb") as destination:
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

    def delete_owner_dir(self, namespace: str, owner_id: uuid.UUID) -> None:
        target = self._namespace_dir(namespace, owner_id)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
