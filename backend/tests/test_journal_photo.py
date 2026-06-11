from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.config import settings
from app.main import app
from app.media.storage import MAX_BYTES

EntryBuilder = Callable[..., dict[str, object]]

JPEG_HEADER = b"\xff\xd8\xff\xe0"


def _jpeg_bytes(trailing: bytes = b"") -> bytes:
    return JPEG_HEADER + trailing


@pytest.fixture
def media_root_override(tmp_path: Path) -> Iterator[Path]:
    from app.media.deps import get_media_storage
    from app.media.storage import MediaStorage

    def _override() -> MediaStorage:
        return MediaStorage(media_root=tmp_path)

    app.dependency_overrides[get_media_storage] = _override
    try:
        yield tmp_path
    finally:
        app.dependency_overrides.pop(get_media_storage, None)


async def _create_entry(
    client: AsyncClient, pet_id: object, valid_journal_entry: EntryBuilder
) -> str:
    response = await client.post(f"/pets/{pet_id}/journal", json=valid_journal_entry())
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def test_attach_photo_sets_path_and_url(
    authenticated_client: AsyncClient,
    media_root_override: Path,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    entry_id = await _create_entry(authenticated_client, journal_pet["id"], valid_journal_entry)
    upload_bytes = _jpeg_bytes(trailing=b"tail")

    response = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal/{entry_id}/photo",
        files={"file": ("poop.jpg", upload_bytes, "image/jpeg")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["photo_path"].startswith(f"journal/{journal_pet['id']}/")
    base = settings.backend_base_url.rstrip("/")
    version = body["photo_path"].rsplit("/", 1)[-1].split(".", 1)[0]
    assert (
        body["photo_url"] == f"{base}/pets/{journal_pet['id']}/journal/{entry_id}/photo?v={version}"
    )
    assert (media_root_override / body["photo_path"]).read_bytes() == upload_bytes


async def test_get_photo_streams_file(
    authenticated_client: AsyncClient,
    media_root_override: Path,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    entry_id = await _create_entry(authenticated_client, journal_pet["id"], valid_journal_entry)
    upload_bytes = _jpeg_bytes(trailing=b"streamed")
    await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal/{entry_id}/photo",
        files={"file": ("photo.jpg", upload_bytes, "image/jpeg")},
    )

    response = await authenticated_client.get(f"/pets/{journal_pet['id']}/journal/{entry_id}/photo")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == upload_bytes


async def test_get_photo_without_photo_is_404(
    authenticated_client: AsyncClient,
    media_root_override: Path,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    entry_id = await _create_entry(authenticated_client, journal_pet["id"], valid_journal_entry)

    response = await authenticated_client.get(f"/pets/{journal_pet['id']}/journal/{entry_id}/photo")

    assert response.status_code == 404
    assert response.json()["detail"] == "ENTRY_PHOTO_NOT_FOUND"


async def test_replacing_photo_deletes_prior_file(
    authenticated_client: AsyncClient,
    media_root_override: Path,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    entry_id = await _create_entry(authenticated_client, journal_pet["id"], valid_journal_entry)
    first = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal/{entry_id}/photo",
        files={"file": ("a.jpg", _jpeg_bytes(b"first"), "image/jpeg")},
    )
    first_path = media_root_override / first.json()["photo_path"]

    second = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal/{entry_id}/photo",
        files={"file": ("b.jpg", _jpeg_bytes(b"second"), "image/jpeg")},
    )
    second_path = media_root_override / second.json()["photo_path"]

    assert second.status_code == 200
    assert not first_path.exists()
    assert second_path.read_bytes() == _jpeg_bytes(b"second")


async def test_detach_photo_removes_file_and_clears_path(
    authenticated_client: AsyncClient,
    media_root_override: Path,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    entry_id = await _create_entry(authenticated_client, journal_pet["id"], valid_journal_entry)
    attached = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal/{entry_id}/photo",
        files={"file": ("a.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    photo_file = media_root_override / attached.json()["photo_path"]

    detach = await authenticated_client.delete(
        f"/pets/{journal_pet['id']}/journal/{entry_id}/photo"
    )
    refetched = await authenticated_client.get(f"/pets/{journal_pet['id']}/journal/{entry_id}")

    assert detach.status_code == 204
    assert not photo_file.exists()
    assert refetched.json()["photo_path"] is None
    assert refetched.json()["photo_url"] is None


async def test_deleting_entry_deletes_photo_file(
    authenticated_client: AsyncClient,
    media_root_override: Path,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    entry_id = await _create_entry(authenticated_client, journal_pet["id"], valid_journal_entry)
    attached = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal/{entry_id}/photo",
        files={"file": ("a.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    photo_file = media_root_override / attached.json()["photo_path"]

    response = await authenticated_client.delete(f"/pets/{journal_pet['id']}/journal/{entry_id}")

    assert response.status_code == 204
    assert not photo_file.exists()


async def test_attach_rejects_unsupported_media_type(
    authenticated_client: AsyncClient,
    media_root_override: Path,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    entry_id = await _create_entry(authenticated_client, journal_pet["id"], valid_journal_entry)

    response = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal/{entry_id}/photo",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "ENTRY_PHOTO_UNSUPPORTED_MEDIA_TYPE"


async def test_attach_rejects_oversized_file(
    authenticated_client: AsyncClient,
    media_root_override: Path,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    entry_id = await _create_entry(authenticated_client, journal_pet["id"], valid_journal_entry)
    oversized = _jpeg_bytes(b"x" * MAX_BYTES)

    response = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal/{entry_id}/photo",
        files={"file": ("big.jpg", oversized, "image/jpeg")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "ENTRY_PHOTO_TOO_LARGE"
