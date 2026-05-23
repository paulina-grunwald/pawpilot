from __future__ import annotations

import io
import uuid
from pathlib import Path

import pytest

from app.media.storage import (
    MAX_BYTES,
    MediaStorage,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
)


@pytest.fixture
def media_storage(tmp_path: Path) -> MediaStorage:
    return MediaStorage(media_root=tmp_path)


def _bytes_reader(payload: bytes) -> io.BytesIO:
    return io.BytesIO(payload)


def test_save_writes_file_under_namespace_owner_path(media_storage: MediaStorage) -> None:
    owner_id = uuid.uuid4()
    stored = media_storage.save(
        namespace="pets",
        owner_id=owner_id,
        content_type="image/jpeg",
        fileobj=_bytes_reader(b"jpeg-bytes"),
    )

    assert stored.relative_path.startswith(f"pets/{owner_id}/")
    assert stored.relative_path.endswith(".jpg")
    assert stored.absolute_path.exists()
    assert stored.absolute_path.read_bytes() == b"jpeg-bytes"


def test_save_assigns_extension_for_each_supported_mime(media_storage: MediaStorage) -> None:
    owner_id = uuid.uuid4()
    pairs = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
    }
    for mime, expected_extension in pairs.items():
        stored = media_storage.save(
            namespace="pets",
            owner_id=owner_id,
            content_type=mime,
            fileobj=_bytes_reader(b"data"),
        )
        assert stored.relative_path.endswith(expected_extension), mime


def test_save_rejects_unsupported_mime_type(media_storage: MediaStorage) -> None:
    with pytest.raises(UnsupportedMediaTypeError):
        media_storage.save(
            namespace="pets",
            owner_id=uuid.uuid4(),
            content_type="image/heic",
            fileobj=_bytes_reader(b"x"),
        )


def test_save_rejects_payload_exceeding_max_bytes(media_storage: MediaStorage) -> None:
    too_large = b"x" * (MAX_BYTES + 1)
    with pytest.raises(PayloadTooLargeError):
        media_storage.save(
            namespace="pets",
            owner_id=uuid.uuid4(),
            content_type="image/jpeg",
            fileobj=_bytes_reader(too_large),
        )


def test_save_cleans_up_partial_file_when_size_check_fails(
    media_storage: MediaStorage, tmp_path: Path
) -> None:
    too_large = b"y" * (MAX_BYTES + 8)
    with pytest.raises(PayloadTooLargeError):
        media_storage.save(
            namespace="pets",
            owner_id=uuid.uuid4(),
            content_type="image/jpeg",
            fileobj=_bytes_reader(too_large),
        )
    leftover = list((tmp_path / "pets").rglob("*"))
    assert all(path.is_dir() for path in leftover), leftover


def test_delete_is_idempotent_for_missing_files(media_storage: MediaStorage) -> None:
    media_storage.delete("pets/nonexistent/missing.jpg")
    media_storage.delete(None)


def test_delete_removes_existing_file(media_storage: MediaStorage) -> None:
    owner_id = uuid.uuid4()
    stored = media_storage.save(
        namespace="pets",
        owner_id=owner_id,
        content_type="image/png",
        fileobj=_bytes_reader(b"png"),
    )
    assert stored.absolute_path.exists()

    media_storage.delete(stored.relative_path)
    assert not stored.absolute_path.exists()


def test_delete_owner_dir_removes_subtree(media_storage: MediaStorage, tmp_path: Path) -> None:
    owner_id = uuid.uuid4()
    for _ in range(3):
        media_storage.save(
            namespace="pets",
            owner_id=owner_id,
            content_type="image/jpeg",
            fileobj=_bytes_reader(b"x"),
        )
    owner_dir = tmp_path / "pets" / str(owner_id)
    assert owner_dir.exists()

    media_storage.delete_owner_dir("pets", owner_id)
    assert not owner_dir.exists()


def test_delete_owner_dir_is_noop_when_dir_missing(media_storage: MediaStorage) -> None:
    media_storage.delete_owner_dir("pets", uuid.uuid4())


def test_delete_refuses_paths_outside_media_root(
    media_storage: MediaStorage, tmp_path: Path
) -> None:
    sensitive_file = tmp_path.parent / "outside.txt"
    sensitive_file.write_text("important")
    try:
        media_storage.delete(f"../{sensitive_file.name}")
        assert sensitive_file.exists(), "file outside media_root must not be unlinked"
    finally:
        if sensitive_file.exists():
            sensitive_file.unlink()
