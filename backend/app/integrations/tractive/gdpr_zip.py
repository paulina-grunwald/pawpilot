"""Read a Tractive GDPR-export zip into ``GdprExportPayloads``.

Tractive's GDPR export is a ``.zip`` containing the five JSON files we care
about, typically inside a top-level folder named after the request id. We
search recursively so the layout doesn't matter.

Includes a zip-bomb guard: rejects any archive whose total uncompressed
content size exceeds ``MAX_GDPR_ZIP_UNCOMPRESSED_BYTES`` (100 MB by default —
generous enough for multi-year exports but bounded).
"""

from __future__ import annotations

import json
import zipfile
from io import BytesIO

from app.integrations.tractive.consolidate import GDPR_FILENAMES, GdprExportPayloads

MAX_GDPR_ZIP_UNCOMPRESSED_BYTES = 100 * 1024 * 1024


class GdprZipError(ValueError):
    """Raised when the uploaded zip can't be turned into a valid payload set."""


def load_gdpr_export_zip(content: bytes) -> GdprExportPayloads:
    """Parse a zip's bytes into ``GdprExportPayloads``.

    Raises ``GdprZipError`` if the bytes aren't a valid zip, the archive is
    too large uncompressed, or any of the five expected JSON files is missing.
    """
    try:
        archive = zipfile.ZipFile(BytesIO(content))
    except zipfile.BadZipFile as error:
        raise GdprZipError("uploaded file is not a valid zip archive") from error

    with archive:
        total_uncompressed = sum(info.file_size for info in archive.infolist())
        if total_uncompressed > MAX_GDPR_ZIP_UNCOMPRESSED_BYTES:
            raise GdprZipError(
                f"zip contents exceed {MAX_GDPR_ZIP_UNCOMPRESSED_BYTES} bytes uncompressed"
            )

        required_basenames = set(GDPR_FILENAMES.values())
        members_by_basename: dict[str, zipfile.ZipInfo] = {}
        for info in archive.infolist():
            if info.is_dir():
                continue
            basename = info.filename.rsplit("/", 1)[-1]
            if basename in required_basenames and basename in members_by_basename:
                raise GdprZipError(f"zip contains duplicate required file: {basename}")
            members_by_basename[basename] = info

        loaded: dict[str, list[dict[str, object]]] = {}
        for field, filename in GDPR_FILENAMES.items():
            member = members_by_basename.get(filename)
            if member is None:
                raise GdprZipError(f"zip is missing required file: {filename}")
            with archive.open(member) as handle:
                try:
                    loaded[field] = json.loads(handle.read())
                except json.JSONDecodeError as error:
                    raise GdprZipError(f"{filename} is not valid JSON") from error

    return GdprExportPayloads(**loaded)
