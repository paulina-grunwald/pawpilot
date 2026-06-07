# scripts/

Reusable data-prep scripts.

## consolidate_tractive.py

Moved to `backend/scripts/consolidate_tractive.py` — the consolidation logic
now lives in `backend/app/integrations/tractive/` so it can be reused by the
ingestion service as well as the CLI.

Run from the `backend/` directory:

```bash
# default: reads ../data, writes ../data/processed/
cd backend
uv run python scripts/consolidate_tractive.py

# or point at a different export
uv run python scripts/consolidate_tractive.py /path/to/another/export
```

### Next time you get a fresh export

1. Drop the new JSONs into `data/` (overwriting old ones)
2. From `backend/`: `uv run python scripts/consolidate_tractive.py`
3. Read `data/processed/summary.md`

### What it computes per day

- **Activity by category** — decoded from `activity_data.json`'s run-length-encoded
  per-second timeline. Categories `-1, 0, 1, 6, 7, null` map to
  `active / low_intensity / moderate / night_sleep / day_sleep / no_signal`.
  Mapping verified against `progress.achieved_minutes` from Tractive's API.
- **Hourly heatmap** — minutes per category per local hour of day.
- **Resting HR / RR** — flattened samples with mean / min / max / count.
- **Distance walked (km)** — haversine over `position_reports.json`. Filters out
  `sensor_used: PHONE` (owner's phone, not the dog) and pairs implying
  >50 km/h (bad GPS fixes).
- **Tracker stats** — battery range, temperature range, charging-event count.

### Required input files in the export directory

- `activity_data.json`
- `position_reports.json`
- `hardware_reports.json`
- `resting_heart_rates.json`
- `resting_respiratory_rates.json`

Optional / unused (yet): `barks.json`, `geofences.json`, `network_reports.json`,
`pet_zones.json`, `power_saving_zones.json`, `wifi_reports.json`,
`server_commands.json`.
