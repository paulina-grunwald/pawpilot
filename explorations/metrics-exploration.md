# Metrics Exploration — Tractive GDPR Export

> **Superseded by [`metrics-exploration-validated.md`](metrics-exploration-validated.md).**
> This file is the original speculative wishlist. Several items here were later computed against
> the real data and did **not** hold up (notably the "international travel / Den Haag" story, the
> deep/light sleep proxy, HRV, and battery/temperature health metrics). Treat the validated
> document as the source of truth; this one is kept for history.

_Deep read of `data/*.json` (12 files from the Tractive GDPR export). Today we extract roughly 30% of the available signal — mostly aggregates. Lots of compound metrics are sitting unused._

## What we already extract

Activity minutes per category, hourly bucket, resting HR/RR mean·min·max, distance walked, battery range, temperature range, charge starts.
(See `data/processed/summary.md` and `data/processed/per_day.json`.)

---

## What we're missing — per file

### `activity_data.json` (25 days, RLE-encoded categories)
- **Sleep architecture** — wakeups per night (count of transitions out of `night_sleep`), sleep efficiency (% of nighttime block actually asleep), bedtime / wake time per day
- **Longest active bout** & **activity bout count** — walks vs zoomies vs short bursts
- **Circadian fingerprint** — average wake hour, bedtime hour, "weekend shift"
- **Activity intensity ratio** — moderate / low / active distribution as a wellness signal
- **"Restlessness score"** — micro-transitions during night blocks

### `position_reports.json` (6,855 fixes — the goldmine, almost untapped)
- **Outing detection** via `geofence_state.changes_computed` → number of walks per day, time-away-from-home, walk start/end timestamps
- **Walk routes** — sequences of fixes between geofence exits/entries (map-able)
- **Walking speed** — m/s between consecutive fixes → average pace, top speed (sprint detection)
- **Places visited** — DBSCAN-style clustering on lat/lng → "favorite spots"
- **Indoor vs outdoor split** — `sensor_used` ratio (GPS vs `KNOWN_WIFI` vs cellular)
- **GPS accuracy timeline** — `hori_accuracy` distribution
- **Elevation profile** — `alt` deltas per walk
- **Home dwell time** per day (geofence inside-state minutes)

### `hardware_reports.json` (5,707 records)
- **Battery drain rate** %/hour — health trend over weeks
- **Charging behavior** — total charging hours/day, charge cycles, time-to-full
- **Stationary streaks** — `stationary_for_seconds` peaks (collar-off vs dog-sleeping)
- **Deep power-saving %** — proxy for time spent in named safe zones
- **Thermal anomalies** — temperature outliers (sun exposure / left in car / etc.)
- **Power-saving-zone occupancy** — which named zone (Home / Den Haag / etc.) per hour

### `network_reports.json` (4,321 records, currently 0% used)
- **Connectivity quality timeline** — RSRP/RSRQ → "signal was bad here" overlays
- **Cell handovers** (`cell_change_count`) — independent movement proxy when GPS is off
- **TAC changes** — crossed tracking-area boundaries (city-scale travel)
- **Country/operator footprint** — MCC 226 = Romania. Compare with `power_saving_zones.json` "Den Haag" (MCC 204 = Netherlands) → **the tracker traveled internationally**, that's a story we can tell

### `resting_heart_rates.json` / `resting_respiratory_rates.json`
- **HRV-ish metric** — each record has multi-sample bursts (e.g. `[70,70,70,65,65]`); compute SDNN-style variance
- **Vital trend lines** — 7-day rolling average + z-score for anomaly flagging
- **Diurnal HR/RR curve** — by hour-of-day overlay
- **Co-occurrence with activity** — HR/RR in the 15 min after a walk (recovery)

### `server_commands.json` / `barks.json` / `wifi_reports.json`
- LED / find-mode usage count (light)
- Bark events (currently empty in this export)
- Nearby SSID fingerprint (privacy-sensitive — skip for UI)

---

## Compound metrics (cross-signal — most interesting)

1. **Walk Card** — fuse geofence exit + GPS route + activity minutes + post-walk HR recovery into one card:
   _"Walk #3, 18:42, 1.4 km, 22 min, peak HR 88, recovery 4 min"_
2. **PawScore™ daily wellness** — weighted blend of (sleep efficiency, active minutes vs baseline, HR within band, RR within band, charging consistency)
3. **"Was it a good day?"** — anomaly flag: any vital > 2σ from rolling 14-day mean
4. **Travel detector** — TAC changes + MCC jump + power-saving-zone shifts → trip timeline
5. **Sleep recovery score** — overnight resting HR mean vs prior-day activity load
6. **Outing timeline** — per-day strip showing home / walk / home / walk / home with durations

---

## Suggested next bites (high impact, low effort)

- **Outings per day + walk durations** (geofence transitions on `position_reports.json`) — most user-visible
- **Sleep continuity** (wakeups, bedtime, wake time) — already have the RLE, just walk it differently
- **HR / RR rolling baseline + anomaly flag** — small math, big "vet alert" UX win
- **Walk route polylines** — drop on a Mapbox / Leaflet view for the detail page

---

## Raw file inventory

| File | Size | Records | Currently used? |
|---|---:|---:|---|
| `activity_data.json` | 632K | 25 days | ✅ partial (minutes + hourly) |
| `barks.json` | 2B | 0 | — empty |
| `geofences.json` | 264B | 1 | ✅ config |
| `hardware_reports.json` | 1.8M | 5,707 | ✅ partial (battery/temp ranges) |
| `network_reports.json` | 1.1M | 4,321 | ❌ unused |
| `pet_zones.json` | 167B | 1 | ✅ config |
| `position_reports.json` | 3.1M | 6,855 | ✅ partial (distance + count) |
| `power_saving_zones.json` | 663B | 3 | ✅ config |
| `resting_heart_rates.json` | 28K | 25 days | ✅ partial (mean/min/max) |
| `resting_respiratory_rates.json` | 23K | 25 days | ✅ partial (mean/min/max) |
| `server_commands.json` | 585B | 2 | ❌ unused |
| `wifi_reports.json` | 4.8K | 4 | ❌ unused |
