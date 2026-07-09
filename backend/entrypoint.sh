#!/bin/sh
set -e

# Runs as root so MEDIA_ROOT stays writable even when it is a volume mount
# (mounts arrive root-owned); the app itself runs as pawpilot.
mkdir -p "$MEDIA_ROOT"
chown pawpilot:pawpilot "$MEDIA_ROOT"

exec runuser -u pawpilot -- sh -c 'alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"'
