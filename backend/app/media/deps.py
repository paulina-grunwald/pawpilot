from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.config import settings
from app.media.storage import LocalMediaStorage, MediaStorage, S3MediaStorage


def get_media_root() -> Path:
    return Path(settings.media_root).resolve()


@lru_cache(maxsize=1)
def _s3_media_storage() -> S3MediaStorage:
    import boto3
    from botocore.config import Config

    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
        # MinIO serves buckets on paths, not subdomains.
        config=Config(s3={"addressing_style": "path"}),
    )
    return S3MediaStorage(client=client, bucket=settings.s3_bucket)


def get_media_storage() -> MediaStorage:
    if settings.media_backend == "s3":
        return _s3_media_storage()
    return LocalMediaStorage(media_root=get_media_root())
