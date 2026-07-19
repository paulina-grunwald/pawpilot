# Metrics Exploration (Validated) — Tractive GDPR Export

_Successor to [`metrics-exploration.md`](metrics-exploration.md), which was a speculative
wishlist. This document keeps only what survives computation against the real data, and
records what died and why. Every claim below carries a real number computed from
`data/*.json` (Haru, an Australian Shepherd, 25 days: 2026-04-29 to 2026-05-23)._

## How this was validated

Five metric families were computed against the raw files, then each candidate that looked
promising was handed to an independent skeptic instructed to _refute_ it (default to refuting
if uncertain), re-deriving every number from scratch. A metric only earns a recommendation if
the signal is distinguishable from artifact with one dog and 25 days, is not confounded by
collar-off / charging / sparse sampling, and would not mislead an owner about their dog's
health. Twenty of twenty-three promising candidates were knocked down to "weak" or killed
outright. The survivors, and the honest reduced forms of the near-misses, are below.

Two of the three findings that survived even the harshest review are not new charts at all.
They are **data-correctness bugs the new features must not be built on top of.**

---

## Blockers (fix before building anything intraday or GPS-based)

### P0-A — the activity RLE is decoded 3 hours off (bug in shipped code)

`decode_activity_day` ([`backend/app/integrations/tractive/consolidate.py:245`](../backend/app/integrations/tractive/consolidate.py))
treats `cursor = 0` as **GMT** midnight and then adds the timezone offset a second time:
`local_hour = int(((cursor // 3600) + offset_hours) % 24)`. The run-length timeline actually
starts at **local** midnight.

Proof, using GPS fixes (which carry absolute UTC timestamps, so they are independent of the
activity encoding): bin "active fraction by cursor-hour" against "GPS away-from-home fraction
by UTC hour" and sweep the alignment.

| Alignment | Correlation with GPS away-from-home |
|---|---|
| cursor = local midnight (correct) | **+0.952** |
| cursor = GMT midnight (backend's assumption) | **−0.142** |

The active peak (local 08:00) coincides exactly with the GPS away-from-home peak, and the
best alignment is local-start on 24 of 24 days. The fix is to drop the second offset:
`local_hour = int((cursor // 3600) % 24)`.

Impact: daily totals for active / low / moderate / no_signal are hour-independent and do not
change. The night-versus-day **sleep split** shifts by mean 37 min/day (max 3.0h). The
`hourly_minutes_by_category` matrix, which is already shipped to the frontend and currently
discarded, is rotated a full 3 hours. Any intraday or circadian view depends on this.

### P0-B — the geofence config is stale; the household moved (around Aug 2025, owner-confirmed)

All 2,880 in-window GPS fixes report `is_inside = false` for the configured "Home" fence, and
a haversine recomputation agrees 100%. The configured fence (44.41922, 26.007004) is **3.5 km**
from where the dog now lives (densest fix cluster 44.4488, 26.0221, which is 25 m from the
`power_saving_zones` "home lacul mori" zone, `last_seen 2026-05-22`). The full-year GPS
timeline is a clean step function: last fix near the old home 2025-08-13, zero after.
`geofences.json.updated_at` is 2025-08-13 — touched the day of the move and still wrong.

Consequence: any GPS/geofence feature must **derive home from the data**, not trust
`geofences.json`. Using the config as-is would report "time at home = 0h" every day and fire a
permanent "left the safe zone" alert.

---

## The two questions that prompted this

**Daily heart-rate graph — yes, but do it honestly.** `heart_rate_mean` already arrives in the
API and is typed in the frontend, rendered only as a number
([`frontend/lib/tractive.format.ts:142`](../frontend/lib/tractive.format.ts)). `LineChart`
even carries an unused `baseline?:{low,high}` band prop. The naive wire-up is nearly free and
misleading: the visible day-to-day HR wiggle is confounded with how often the collar sampled
(r = +0.38 between daily mean and sample count), a single motion-contaminated burst
`[146,146,146]` on 2026-05-19 sets the range, the "trend" the chart implies is absent
(slope +0.09 bpm/day, p = 0.38), and the 50-130 band cannot fire (50 is the sensor floor; the
range is self-documented as a placeholder). The honest version aggregates at record level,
suppresses low-sample days (only 2026-05-16 has n < 10), rejects non-resting bursts, shows
per-day confidence, and avoids clinical-band and trend language. See spec 017.

**Deep / light sleep — not derivable from this export.** There are no sleep stages in the data.
What exists is one rest bundle (code 6, fragmented: 10,805 runs, median run 21 s) and daytime
naps (code 7: 43 runs, median run 39 min). Testing whether 6-vs-7 could stand in for deep-vs-light
fails; labeling it so would be dishonest. The legitimate alternative is **sleep architecture**:
nightly consolidated bouts (longest bout 167-485 min across days, mean 336), a fragmentation
index (3.3-22.4 arousals/hr), and total night rest. See spec 019.

---

## Recommended (survived review, at the stated framing)

Grouped by cost. Real numbers are the evidence.

### Free — data already on the wire, frontend-only (after P0-A)
- **Intraday activity heatmap.** `hourly_minutes_by_category` is a full 24h × category matrix
  already sent to the frontend and discarded. A day × hour "when is Haru active" heatmap is
  honest once the 3h rotation is fixed. Peak active hour is local 08:00.
- **Data-coverage caveat.** `minutes_no_signal` is already in the API. Surface as a neutral
  "N h of this day has no activity data; totals are a floor." Never a green "trustworthy" badge
  (charger-on-a-shelf scores as rest). Days with no_signal > 120 min: 6/25.
- **Data-driven activity goal.** Haru does a median **270 min/day** active (mean 286, p25 231,
  p75 349); **24 of 25 days already beat** the hardcoded 140-minute goal. Replace it with a
  per-pet target (rolling median, or the `pets.daily_active_target_minutes` column the code TODO
  already anticipates).

### Cheap — rollup column + small ingest change
- **Honest daily HR line chart.** Record-level daily resting HR with per-day confidence and
  low-n suppression; no clinical band, no trend language. (Direct answer to question 1.)
- **Honest daily RR line chart.** Same shape; RR range 7-39, mean 19.2. Plus one genuinely
  robust finding worth a small callout: resting RR is reliably lower at night (this survived
  every adversarial attack, and is the clinically meaningful direction for dogs).

### Meaty — new parsing / ingest
- **Walks & outings (gated on P0-B).** Real: **~2.7-3.6 outings/day, present on 25/25 days,
  median ~35 min**, walk-like speeds (median ~1.0 m/s), median max-distance-from-home ~0.8 km.
  Frame the count as "at least N" (14% of the window has no GPS coverage). Ship a GPS-only walk
  card; drop the activity-fusion "cross-validation" (it is circular sensor coupling).
- **Sleep architecture** (the deep/light alternative above).

---

## Rejected — do not build (each refuted with numbers)

- **Deep/light sleep stages, HRV.** Not in the data; the HR values are bpm, not R-R intervals.
- **RR > 30 heart-failure alert.** Would fire on 22/25 days because the "resting" readings are
  motion-contaminated. Alarm fatigue, and it desensitizes a genuinely dangerous future signal.
- **"Was it a good day?" composite / PawScore.** Active-minutes is bimodal; the score is
  noise-dominated and either flattens or false-flags.
- **Battery health / drain rate.** `battery_level` is a coarse voltage lookup table; drain rate
  is an artifact of it.
- **Tracker temperature as health.** The 50°C max on 2026-04-29 coincides with a charging
  session — it is device electronics heat, not the dog. Misleading to show.
- **Travel timeline ("Den Haag").** The move is real — the family relocated from The Hague to
  Bucharest around mid-2024 (owner-confirmed) — but it predates this export's window: every one
  of the 6,855 GPS fixes (first: 2025-05-23) sits in a 5.8 × 3.4 km box around Bucharest, and
  4,318/4,321 network records are MCC 226 (Romania). The "Den Haag" `power_saving_zones` entry
  (`last_seen 2024-06-30`) is genuine history, not a config error — there is just nothing
  in-window to chart. A travel feature could only light up on a future export that spans a move.
- **Indoor/outdoor split via `sensor_used`.** Tautological — KNOWN_WIFI fixes snap to a single
  router coordinate (1,676 of 1,889 are byte-identical), carrying no positional information.
- **Walk-activity "fusion cross-validation".** Circular: the collar emits a GNSS fix on motion
  and falls back to WiFi at rest, so "away + active" is two readouts of one motion sensor.

---

## Data-trust rules (every new chart must respect these)

1. **Min-n suppression** — do not plot a daily vital below a sample-count threshold; mark or
   drop it (2026-05-16 HR has n = 5).
2. **Record-level, not sample-level** — samples arrive in bursts; treating a burst of 3 as 3
   independent draws overstates precision. Aggregate per record.
3. **Artifact rejection** — drop non-resting bursts (e.g. `[146,146,146]`) before computing a
   daily resting vital.
4. **no_signal is a floor, not zero** — always caveat coverage; never render "100% trustworthy."
5. **No placeholder-as-clinical** — the 50-130 / 8-40 ranges are self-documented placeholders;
   do not present them as breed-appropriate normal bands.
6. **Derive home from data** — never trust `geofences.json` for this dog.

---

## What ships from here

- Specs: `016-tractive-decode-timezone-fix`, `017-vitals-intraday-dashboard`,
  `018-walks-outings`, `019-sleep-architecture` (local; `specs/` is gitignored).
- A visual mockup of the proposed charts rendered on Haru's real 25 days.
- Then the PR stack (smallest-first, each under ~1000 hand-written lines), P0-A first.

## Raw file inventory (usage after this work)

| File | Records | Status |
|---|---:|---|
| `activity_data.json` | 25 days | used (decode fix in P0-A; heatmap + sleep architecture) |
| `position_reports.json` | 6,855 | partial today (distance); walks in spec 018 |
| `hardware_reports.json` | 5,707 | partial (battery/temp range) — no new health metric survived |
| `resting_heart_rates.json` | 25 days | mean only today; honest daily chart in spec 017 |
| `resting_respiratory_rates.json` | 25 days | mean only today; honest daily chart in spec 017 |
| `network_reports.json` | 4,321 | stays unused (the Hague→Bucharest move predates the export window) |
| `geofences.json` / `pet_zones.json` | 1 each | stale (P0-B) — derive home from data instead |
| `power_saving_zones.json` | 3 | used only to cross-check derived home |
| `barks.json` / `server_commands.json` / `wifi_reports.json` | 0 / 2 / 4 | nothing to build |
