from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.media.storage import MediaStorage


def get_media_root() -> Path:
    return Path(settings.media_root).resolve()


def get_media_storage() -> MediaStorage:
    return MediaStorage(media_root=get_media_root())
