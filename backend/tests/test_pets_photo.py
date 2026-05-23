from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.config import settings
from app.main import app
from app.media.deps import get_media_root
from app.media.storage import MAX_BYTES

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


async def test_upload_photo_writes_file_and_sets_photo_url(
    authenticated_client: AsyncClient,
    media_root_override: Path,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    upload_bytes = _jpeg_bytes(trailing=b"tail")
    response = await authenticated_client.post(
        f"/pets/{pet_id}/photo",
        files={"file": ("photo.jpg", upload_bytes, "image/jpeg")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["photo_path"] is not None
    assert body["photo_path"].startswith(f"pets/{pet_id}/")
    base = settings.backend_base_url.rstrip("/")
    assert body["photo_url"] == f"{base}/media/{body['photo_path']}"

    written = media_root_override / body["photo_path"]
    assert written.exists()
    assert written.read_bytes() == upload_bytes


async def test_upload_photo_rejects_unsupported_media_type(
    authenticated_client: AsyncClient,
    media_root_override: Path,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    response = await authenticated_client.post(
        f"/pets/{pet_id}/photo",
        files={"file": ("photo.heic", b"\x00", "image/heic")},
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "PET_PHOTO_UNSUPPORTED_MEDIA_TYPE"


async def test_upload_photo_rejects_missing_content_type(
    authenticated_client: AsyncClient,
    media_root_override: Path,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    response = await authenticated_client.post(
        f"/pets/{pet_id}/photo",
        files={"file": ("photo.bin", b"abc", "")},
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "PET_PHOTO_UNSUPPORTED_MEDIA_TYPE"


async def test_upload_photo_rejects_files_above_max_bytes(
    authenticated_client: AsyncClient,
    media_root_override: Path,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    too_large = _jpeg_bytes(trailing=b"x" * (MAX_BYTES + 1))
    response = await authenticated_client.post(
        f"/pets/{pet_id}/photo",
        files={"file": ("photo.jpg", too_large, "image/jpeg")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "PET_PHOTO_TOO_LARGE"


async def test_second_upload_replaces_first_photo_on_disk(
    authenticated_client: AsyncClient,
    media_root_override: Path,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    first = await authenticated_client.post(
        f"/pets/{pet_id}/photo",
        files={"file": ("a.jpg", _jpeg_bytes(b"first"), "image/jpeg")},
    )
    first_path = media_root_override / first.json()["photo_path"]

    second = await authenticated_client.post(
        f"/pets/{pet_id}/photo",
        files={"file": ("b.jpg", _jpeg_bytes(b"second"), "image/jpeg")},
    )
    second_path = media_root_override / second.json()["photo_path"]

    assert first_path != second_path
    assert not first_path.exists(), "prior file should be removed"
    assert second_path.exists()


async def test_delete_photo_endpoint_clears_path_and_file(
    authenticated_client: AsyncClient,
    media_root_override: Path,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    uploaded = await authenticated_client.post(
        f"/pets/{pet_id}/photo",
        files={"file": ("p.jpg", _jpeg_bytes(b"abc"), "image/jpeg")},
    )
    photo_path = uploaded.json()["photo_path"]
    on_disk = media_root_override / photo_path

    response = await authenticated_client.delete(f"/pets/{pet_id}/photo")
    assert response.status_code == 200
    assert response.json()["photo_path"] is None
    assert response.json()["photo_url"] is None
    assert not on_disk.exists()


async def test_delete_photo_endpoint_is_noop_when_no_photo(
    authenticated_client: AsyncClient,
    media_root_override: Path,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]
    assert created.json()["photo_path"] is None

    response = await authenticated_client.delete(f"/pets/{pet_id}/photo")
    assert response.status_code == 200
    assert response.json()["photo_path"] is None
    assert response.json()["photo_url"] is None


async def test_delete_pet_also_removes_photo_files(
    authenticated_client: AsyncClient,
    media_root_override: Path,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    created = await authenticated_client.post("/pets", json=valid_pet_payload())
    pet_id = created.json()["id"]

    uploaded = await authenticated_client.post(
        f"/pets/{pet_id}/photo",
        files={"file": ("p.jpg", _jpeg_bytes(b"abc"), "image/jpeg")},
    )
    photo_path = uploaded.json()["photo_path"]
    on_disk = media_root_override / photo_path

    response = await authenticated_client.delete(f"/pets/{pet_id}")
    assert response.status_code == 204
    assert not on_disk.exists()
    owner_dir = media_root_override / "pets" / pet_id
    assert not owner_dir.exists()


async def test_upload_photo_requires_authentication(
    client: AsyncClient,
    media_root_override: Path,
) -> None:
    response = await client.post(
        "/pets/00000000-0000-0000-0000-000000000000/photo",
        files={"file": ("p.jpg", _jpeg_bytes(b"abc"), "image/jpeg")},
    )
    assert response.status_code == 401


async def test_upload_photo_for_other_users_pet_returns_404(
    authenticated_client: AsyncClient,
    client: AsyncClient,
    media_root_override: Path,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    owned = await authenticated_client.post("/pets", json=valid_pet_payload(name="Owned"))
    pet_id = owned.json()["id"]

    other_email = "intruder@example.com"
    other_password = "another-good-password"
    register = await client.post(
        "/auth/register",
        json={"email": other_email, "password": other_password},
    )
    assert register.status_code == 201
    login = await client.post(
        "/auth/login",
        data={"username": other_email, "password": other_password},
    )
    assert login.status_code == 204

    response = await client.post(
        f"/pets/{pet_id}/photo",
        files={"file": ("p.jpg", _jpeg_bytes(b"abc"), "image/jpeg")},
    )
    assert response.status_code == 404


def test_get_media_root_returns_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "media_root", str(tmp_path))
    resolved = get_media_root()
    assert resolved.is_absolute()
    assert resolved == tmp_path.resolve()
