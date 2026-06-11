#!/usr/bin/env python3
"""Thin CLI wrapper around the Tractive consolidation pipeline.

Reads a Tractive GDPR export directory and writes:
  ``<export_dir>/processed/per_day.json`` — list of PerDayRollup as JSON
  ``<export_dir>/processed/summary.md``   — human-readable Markdown table

Run from the ``backend/`` directory so the ``app`` package is importable:

    uv run python scripts/consolidate_tractive.py                # default: ../data
    uv run python scripts/consolidate_tractive.py path/to/export # custom dir

The export directory must contain at least:
  activity_data.json, position_reports.json, hardware_reports.json,
  resting_heart_rates.json, resting_respiratory_rates.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.integrations.tractive.consolidate import build_per_day, load_gdpr_export
from app.integrations.tractive.markdown import render_summary

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = BACKEND_ROOT.parent / "data"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Consolidate a Tractive GDPR export into per-day JSON + markdown."
    )
    parser.add_argument(
        "data_dir",
        nargs="?",
        type=Path,
        default=DEFAULT_DATA,
        help=f"Path to export directory (default: {DEFAULT_DATA})",
    )
    args = parser.parse_args()
    data_dir: Path = args.data_dir.resolve()
    if not data_dir.is_dir():
        sys.exit(f"error: not a directory: {data_dir}")

    payloads = load_gdpr_export(data_dir)
    rollups = build_per_day(payloads)

    output_dir = data_dir / "processed"
    output_dir.mkdir(exist_ok=True)
    per_day_path = output_dir / "per_day.json"
    summary_path = output_dir / "summary.md"
    per_day_path.write_text(
        json.dumps([rollup.model_dump(mode="json") for rollup in rollups], indent=2)
    )
    summary_path.write_text(render_summary(rollups))
    print(f"Wrote {per_day_path} ({len(rollups)} days)")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
