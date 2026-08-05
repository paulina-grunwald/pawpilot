import type { SleepSplitBar } from "@/app/_components/dashboard/SleepSplitBars";
import type { TodayPanelData } from "@/app/_components/dashboard/TodayPanel/TodayPanel";
import { formatMonthDay, formatWeekday } from "./date";
import type { TractiveDailySummary } from "./tractive";

// TODO: make the daily active target per-pet user-configurable. Right now this
// is a single hardcoded number for all dogs, which doesn't match what users see
// in Tractive's own app where they pick a target during onboarding. Plan:
//   - add `pets.daily_active_target_minutes int` column (nullable, default null)
//   - settings UI on the pet detail page to set/edit it
//   - read it here (fall back to this constant only if the pet hasn't set one)
export const DAILY_ACTIVE_TARGET_MINUTES = 140;

// TODO: replace with breed/age/size-aware norms (see specs/006-tractive-integration.md
// follow-ups + the planned breed_norms table). For now we use generic adult-dog
// safe ranges so the chip is at least directionally honest.
const VITAL_RANGES = {
  restingHeartRateBpm: { low: 50, high: 130 },
  restingRespiratoryRpm: { low: 8, high: 40 },
} as const;

export type VitalsStatus = {
  label: string;
  tone: "positive" | "caution" | "neutral";
};

function computeVitalsStatus(today: {
  heart_rate_mean: number | null;
  respiratory_rate_mean: number | null;
}): VitalsStatus {
  const checks: Array<{ value: number | null; range: { low: number; high: number } }> = [
    { value: today.heart_rate_mean, range: VITAL_RANGES.restingHeartRateBpm },
    { value: today.respiratory_rate_mean, range: VITAL_RANGES.restingRespiratoryRpm },
  ];
  const measured = checks.filter((check) => check.value !== null);
  if (measured.length === 0) {
    return { label: "No vitals yet", tone: "neutral" };
  }
  const outOfRange = measured.some(
    (check) => check.value! < check.range.low || check.value! > check.range.high,
  );
  if (outOfRange) {
    return { label: "Vitals out of range", tone: "caution" };
  }
  return { label: "All vitals normal", tone: "positive" };
}

function formatHoursMinutes(totalMinutes: number): string {
  const minutes = Math.max(0, Math.round(totalMinutes));
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return `${hours}h ${String(remainder).padStart(2, "0")}m`;
}

function totalSleepMinutes(rollup: TractiveDailySummary): number {
  return rollup.minutes_night_sleep + rollup.minutes_day_sleep;
}

function roundedPercent(value: number): number {
  if (!Number.isFinite(value) || value <= 0) return 0;
  return Math.round(value);
}

function meanOfPreceding(
  preceding: readonly TractiveDailySummary[],
  pick: (rollup: TractiveDailySummary) => number,
): number | null {
  if (preceding.length === 0) return null;
  const total = preceding.reduce((sum, rollup) => sum + pick(rollup), 0);
  return total / preceding.length;
}

function deltaCopy(today: number, baseline: number | null, unit: string): string | undefined {
  if (baseline === null) return undefined;
  const deltaValue = today - baseline;
  if (Math.abs(deltaValue) < 0.5) return "matches baseline";
  const direction = deltaValue > 0 ? "↑" : "↓";
  const rounded =
    unit === "km" ? Math.abs(deltaValue).toFixed(1) : String(Math.round(Math.abs(deltaValue)));
  return `${direction} ${rounded} ${unit} vs avg`;
}

/**
 * Turn the latest N rollups into the dashboard's TodayPanelData shape.
 *
 * Returns `undefined` when there are no rollups, which causes TodayPanel to
 * fall back to its "Connect Tractive" placeholder state.
 *
 * "Today" here means the most recent day with data — the user's upload may
 * be historical, and the demo is more useful when the ring reflects real
 * numbers than the literal calendar date.
 */
export function toTodayPanelData(
  rollups: readonly TractiveDailySummary[],
): TodayPanelData | undefined {
  if (rollups.length === 0) return undefined;

  const sorted = [...rollups].sort((a, b) => a.date.localeCompare(b.date));
  const today = sorted[sorted.length - 1];
  const preceding = sorted.slice(0, -1);

  const activeBaseline = meanOfPreceding(preceding, (rollup) => rollup.minutes_active);
  const sleepBaseline = meanOfPreceding(preceding, totalSleepMinutes);
  const distanceBaseline = meanOfPreceding(preceding, (rollup) => rollup.gps_distance_km);
  const calmBaseline = meanOfPreceding(preceding, (rollup) => rollup.minutes_low_intensity);

  // Raw (unclamped) percent — the ActivityRing component caps the visual fill
  // and shifts color when the goal is exceeded.
  const activityPercent = roundedPercent(
    (today.minutes_active / DAILY_ACTIVE_TARGET_MINUTES) * 100,
  );
  const sublabel =
    activityPercent <= 100
      ? `${activityPercent}% of ${DAILY_ACTIVE_TARGET_MINUTES}min goal`
      : `${activityPercent}% — goal smashed`;

  const totalSleepToday = totalSleepMinutes(today);
  const sleepSplitCopy = `${formatHoursMinutes(today.minutes_night_sleep)} night · ${formatHoursMinutes(today.minutes_day_sleep)} naps`;

  return {
    activityPercent,
    activityLabel: formatHoursMinutes(today.minutes_active),
    activitySublabel: sublabel,
    metrics: [
      {
        label: "Active",
        value: String(Math.round(today.minutes_active)),
        unit: "min",
        delta: deltaCopy(today.minutes_active, activeBaseline, "min"),
      },
      {
        label: "Sleep",
        value: formatHoursMinutes(totalSleepToday),
        // Always show the night/day split here — the vs-avg trend lives in
        // the sleep trend chart, and the split is the more useful at-a-glance
        // breakdown for sleep phases.
        delta: sleepSplitCopy,
      },
      {
        label: "Resting HR",
        value: today.heart_rate_mean === null ? "—" : String(Math.round(today.heart_rate_mean)),
        unit: "bpm",
      },
      {
        label: "Respiratory",
        value:
          today.respiratory_rate_mean === null
            ? "—"
            : String(Math.round(today.respiratory_rate_mean)),
        unit: "rpm",
      },
      {
        label: "Distance",
        value: today.gps_distance_km.toFixed(1),
        unit: "km",
        delta: deltaCopy(today.gps_distance_km, distanceBaseline, "km"),
      },
      {
        label: "Calm time",
        value: formatHoursMinutes(today.minutes_low_intensity),
        delta: deltaCopy(today.minutes_low_intensity, calmBaseline, "min"),
      },
    ],
    activityWeekMinutes: sorted.map((row) => Math.round(row.minutes_active)),
    sleepWeekMinutes: sorted.map((row) => Math.round(totalSleepMinutes(row))),
    weekDates: sorted.map((row) => formatMonthDay(row.date)),
    weekDays: sorted.map((row) => formatWeekday(row.date)),
    activityGoal: DAILY_ACTIVE_TARGET_MINUTES,
    activityWeekMean: activeBaseline === null ? undefined : Math.round(activeBaseline),
    sleepWeekMean: sleepBaseline === null ? undefined : Math.round(sleepBaseline),
    vitalsStatus: computeVitalsStatus(today),
  };
}

/** Per-day stacked night/day sleep bars for the SleepSplitBars chart. */
export function toSleepSplitBars(rollups: readonly TractiveDailySummary[]): SleepSplitBar[] {
  return [...rollups]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((rollup) => ({
      date: rollup.date,
      dayLabel: formatMonthDay(rollup.date),
      nightMinutes: rollup.minutes_night_sleep,
      dayMinutes: rollup.minutes_day_sleep,
    }));
}
