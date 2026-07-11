"""Best-effort media cleanup.

Once the database change is committed, the DB is the source of truth. An
object-store delete that fails (transient S3 error, network blip, dropped
worker) must never turn a successful request into a 500 — and must never mask
the original error on a rollback path. These helpers log and swallow cleanup
failures so callers stay correct; the worst case is an orphaned object, which
is recoverable, rather than a failed user-visible operation.
"""

from __future__ import annotations

import logging
import uuid

from app.media.storage import MediaStorage

logger = logging.getLogger(__name__)


async def delete_media_quietly(media: MediaStorage, relative_path: str | None) -> None:
    if not relative_path:
        return
    try:
        await media.delete(relative_path)
    except Exception:
        logger.exception("best-effort media delete failed for %s", relative_path)


async def delete_owner_dir_quietly(
    media: MediaStorage, namespace: str, subject_id: uuid.UUID
) -> None:
    try:
        await media.delete_owner_dir(namespace, subject_id)
    except Exception:
        logger.exception("best-effort media dir delete failed for %s/%s", namespace, subject_id)
