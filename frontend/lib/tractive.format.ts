import type { SleepSplitBar } from "@/app/_components/dashboard/SleepSplitBars";
import type { TodayPanelData } from "@/app/_components/dashboard/TodayPanel/TodayPanel";
import { formatFullDate, formatMonthDay, formatWeekday } from "./date";
import type { TractiveDailySummary } from "./tractive";

// Generic fallback target, used only until enough clean history exists to
// compute a personal goal (see computePersonalActivityGoal). A future
// pets.daily_active_target_minutes column can still override both.
export const DAILY_ACTIVE_TARGET_MINUTES = 140;

// Days with more than this much unclassified time get a coverage caveat, and
// are excluded from the personal-goal median (a charging collar reads as calm,
// which would drag the goal down).
export const COVERAGE_CAVEAT_THRESHOLD_MINUTES = 120;

// Below this many clean history days the personal goal falls back to the
// generic target rather than trusting a median of two or three days.
export const MINIMUM_CLEAN_DAYS_FOR_PERSONAL_GOAL = 5;

// The goal baseline is a fixed trailing window, never the plotted range. Taking
// the median of the days on screen makes the goal move with the 7d/30d/90d
// toggle and puts half of any range below its own goal by construction.
export const GOAL_BASELINE_DAYS = 28;

function median(values: readonly number[]): number {
  const sorted = [...values].sort((first, second) => first - second);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[middle - 1] + sorted[middle]) / 2 : sorted[middle];
}

function hasCleanCoverage(rollup: TractiveDailySummary): boolean {
  return rollup.minutes_no_signal <= COVERAGE_CAVEAT_THRESHOLD_MINUTES;
}

/**
 * Personal daily active-minutes goal: the median of the preceding clean days.
 * Falls back to the generic target while history is thin, so a new upload
 * never sees a goal derived from a couple of days of noise.
 *
 * Deliberate coupling: the goal window is the fetched range, so switching the
 * 7d/30d/90d toggle recomputes the goal from that range's history. The
 * frontend only ever has the fetched days, so a fixed window is not available
 * client-side; a per-pet stored target is the eventual decoupled answer.
 */
export function computePersonalActivityGoal(preceding: readonly TractiveDailySummary[]): number {
  const cleanDays = preceding.filter(hasCleanCoverage);
  if (cleanDays.length < MINIMUM_CLEAN_DAYS_FOR_PERSONAL_GOAL) {
    return DAILY_ACTIVE_TARGET_MINUTES;
  }
  const personalGoal = Math.round(median(cleanDays.map((rollup) => rollup.minutes_active)));
  return personalGoal > 0 ? personalGoal : DAILY_ACTIVE_TARGET_MINUTES;
}

/**
 * Neutral caveat for days where the collar reported no signal for long
 * stretches (off-body or charging). Totals on such days are a floor, and the
 * dashboard should say so rather than present them as complete.
 */
export function toCoverageNote(rollup: TractiveDailySummary): string | undefined {
  if (hasCleanCoverage(rollup)) return undefined;
  const missing = formatHoursMinutes(rollup.minutes_no_signal);
  return `${missing} of this day has no activity data, so totals are a floor, not the full picture.`;
}

// Days with fewer accepted measurement records than this are not plotted:
// a daily mean built on a handful of readings is mostly sampling noise.
export const MINIMUM_RECORDS_FOR_DAILY_VITAL = 10;

// The typical band and the night/day comparison need enough plotted days or
// records to describe anything; below these they are omitted entirely.
export const MINIMUM_DAYS_FOR_TYPICAL_RANGE = 5;
export const MINIMUM_RECORDS_FOR_NIGHT_DAY_COMPARISON = 10;

export type VitalTrendSeries = {
  values: number[];
  days: string[];
  dates: string[];
  latest: number | null;
  typicalRange?: { low: number; high: number };
  measuredDayCount: number;
  suppressedDayCount: number;
};

type DailyVitalReading = {
  recordMean: number | null;
  recordCount: number;
};

function quartiles(sortedValues: readonly number[]): { low: number; high: number } {
  const at = (fraction: number) => sortedValues[Math.floor(fraction * (sortedValues.length - 1))];
  return { low: at(0.25), high: at(0.75) };
}

function toVitalTrendSeries(
  rollups: readonly TractiveDailySummary[],
  pickReading: (rollup: TractiveDailySummary) => DailyVitalReading,
): VitalTrendSeries {
  const sorted = [...rollups].sort((first, second) => first.date.localeCompare(second.date));
  const measured = sorted.filter((rollup) => {
    const reading = pickReading(rollup);
    return reading.recordMean !== null && reading.recordCount > 0;
  });
  const plotted = measured.filter(
    (rollup) => pickReading(rollup).recordCount >= MINIMUM_RECORDS_FOR_DAILY_VITAL,
  );
  const values = plotted.map((rollup) => pickReading(rollup).recordMean as number);
  const sortedValues = [...values].sort((first, second) => first - second);
  return {
    values,
    days: plotted.map((rollup) => formatWeekday(rollup.date)),
    dates: plotted.map((rollup) => formatMonthDay(rollup.date)),
    latest: values.length > 0 ? values[values.length - 1] : null,
    typicalRange:
      values.length >= MINIMUM_DAYS_FOR_TYPICAL_RANGE ? quartiles(sortedValues) : undefined,
    measuredDayCount: measured.length,
    suppressedDayCount: measured.length - plotted.length,
  };
}

export type RespiratoryNightDayComparison = {
  nightMean: number;
  dayMean: number;
  nightRecordCount: number;
  dayRecordCount: number;
};

function weightedMean(pairs: ReadonlyArray<{ mean: number; count: number }>): number {
  const totalCount = pairs.reduce((sum, pair) => sum + pair.count, 0);
  const weightedSum = pairs.reduce((sum, pair) => sum + pair.mean * pair.count, 0);
  return weightedSum / totalCount;
}

/**
 * Range-wide comparison of night vs day resting respiratory rate, the reading
 * vets ask owners to watch at rest. Omitted unless both buckets have enough
 * records to describe honestly. Purely descriptive: no ordering is implied.
 */
export function toRespiratoryNightDayComparison(
  rollups: readonly TractiveDailySummary[],
): RespiratoryNightDayComparison | undefined {
  const nightPairs = rollups
    .filter(
      (rollup) =>
        rollup.respiratory_rate_night_record_mean !== null &&
        rollup.respiratory_rate_night_record_count > 0,
    )
    .map((rollup) => ({
      mean: rollup.respiratory_rate_night_record_mean as number,
      count: rollup.respiratory_rate_night_record_count,
    }));
  const dayPairs = rollups
    .filter(
      (rollup) =>
        rollup.respiratory_rate_day_record_mean !== null &&
        rollup.respiratory_rate_day_record_count > 0,
    )
    .map((rollup) => ({
      mean: rollup.respiratory_rate_day_record_mean as number,
      count: rollup.respiratory_rate_day_record_count,
    }));
  const nightRecordCount = nightPairs.reduce((sum, pair) => sum + pair.count, 0);
  const dayRecordCount = dayPairs.reduce((sum, pair) => sum + pair.count, 0);
  if (
    nightRecordCount < MINIMUM_RECORDS_FOR_NIGHT_DAY_COMPARISON ||
    dayRecordCount < MINIMUM_RECORDS_FOR_NIGHT_DAY_COMPARISON
  ) {
    return undefined;
  }
  return {
    nightMean: Math.round(weightedMean(nightPairs) * 10) / 10,
    dayMean: Math.round(weightedMean(dayPairs) * 10) / 10,
    nightRecordCount,
    dayRecordCount,
  };
}

export type VitalsTrendsData = {
  heartRate: VitalTrendSeries;
  respiratoryRate: VitalTrendSeries;
  respiratoryNightDay?: RespiratoryNightDayComparison;
};

export function toVitalsTrends(rollups: readonly TractiveDailySummary[]): VitalsTrendsData {
  return {
    heartRate: toVitalTrendSeries(rollups, (rollup) => ({
      recordMean: rollup.heart_rate_record_mean,
      recordCount: rollup.heart_rate_record_count,
    })),
    respiratoryRate: toVitalTrendSeries(rollups, (rollup) => ({
      recordMean: rollup.respiratory_rate_record_mean,
      recordCount: rollup.respiratory_rate_record_count,
    })),
    respiratoryNightDay: toRespiratoryNightDayComparison(rollups),
  };
}

export type SleepQualityData = {
  values: number[];
  days: string[];
  dates: string[];
  latestLongestBoutMinutes: number | null;
  averageBoutCount: number | null;
  averageFragmentationIndex: number | null;
  lowCoverageDayCount: number;
  unmeasuredDayCount: number;
};

/**
 * Sleep continuity series: longest consolidated rest bout per day, with the
 * range-wide bout count and fragmentation averages. Continuity only, never
 * clinical sleep stages, and low-coverage days are counted so the card can
 * caveat that missing data understates rest.
 */
export function toSleepQualityData(
  rollups: readonly TractiveDailySummary[],
): SleepQualityData | undefined {
  if (rollups.length === 0) return undefined;
  const sorted = [...rollups].sort((first, second) => first.date.localeCompare(second.date));
  const measured = sorted.filter((rollup) => rollup.sleep_longest_bout_minutes !== null);
  if (measured.length === 0) return undefined;
  const values = measured.map((rollup) => rollup.sleep_longest_bout_minutes as number);
  const boutCounts = measured
    .map((rollup) => rollup.sleep_bout_count)
    .filter((count): count is number => count !== null);
  const fragmentationValues = measured
    .map((rollup) => rollup.sleep_fragmentation_index)
    .filter((value): value is number => value !== null);
  return {
    values,
    days: measured.map((rollup) => formatWeekday(rollup.date)),
    dates: measured.map((rollup) => formatMonthDay(rollup.date)),
    latestLongestBoutMinutes: values.length > 0 ? values[values.length - 1] : null,
    averageBoutCount:
      boutCounts.length > 0
        ? Math.round((boutCounts.reduce((sum, count) => sum + count, 0) / boutCounts.length) * 10) /
          10
        : null,
    averageFragmentationIndex:
      fragmentationValues.length > 0
        ? Math.round(
            (fragmentationValues.reduce((sum, value) => sum + value, 0) /
              fragmentationValues.length) *
              10,
          ) / 10
        : null,
    lowCoverageDayCount: sorted.filter((rollup) => !hasCleanCoverage(rollup)).length,
    unmeasuredDayCount: sorted.length - measured.length,
  };
}

export type OutingRow = {
  startLabel: string;
  durationLabel: string;
  distanceLabel: string;
};

export type OutingsCardData = {
  latestDayLabel: string;
  latestCount: number | null;
  latestRows: OutingRow[];
  rangeDailyAverage: number | null;
  daysInRange: number;
};

// Outing timestamps come back as UTC instants. The dashboard renders them in
// the viewer's timezone, which for an owner looking at their own dog is the
// dog's timezone in all but exotic travel cases.
function formatOutingStart(startedAtIso: string): string {
  const startedAt = new Date(startedAtIso);
  if (Number.isNaN(startedAt.getTime())) return "--:--";
  const hours = String(startedAt.getHours()).padStart(2, "0");
  const minutes = String(startedAt.getMinutes()).padStart(2, "0");
  return `${hours}:${minutes}`;
}

/**
 * Latest-day outings plus a range average, framed as floors throughout:
 * sampling gaps and collar-off time can hide outings, and durations cut off
 * the legs inside the home radius.
 */
export function toOutingsCardData(
  rollups: readonly TractiveDailySummary[],
): OutingsCardData | undefined {
  if (rollups.length === 0) return undefined;
  const sorted = [...rollups].sort((first, second) => first.date.localeCompare(second.date));
  const latest = sorted[sorted.length - 1];
  const measured = sorted.filter((rollup) => rollup.outings_count !== null);
  const totalCount = measured.reduce((sum, rollup) => sum + (rollup.outings_count as number), 0);
  return {
    latestDayLabel: formatMonthDay(latest.date),
    latestCount: latest.outings_count,
    latestRows: latest.outings.map((outing) => ({
      startLabel: formatOutingStart(outing.started_at),
      durationLabel: `at least ${Math.round(outing.duration_minutes)} min`,
      distanceLabel: `up to ${(Math.round(outing.max_distance_meters / 100) / 10).toFixed(1)} km away`,
    })),
    rangeDailyAverage:
      measured.length > 1 ? Math.round((totalCount / measured.length) * 10) / 10 : null,
    daysInRange: measured.length,
  };
}

export type IntradayActivityRow = {
  date: string;
  dayLabel: string;
  hourlyActiveMinutes: number[];
  lowCoverage: boolean;
};

export type IntradayActivityMatrix = {
  rows: IntradayActivityRow[];
  maxActiveMinutes: number;
};

/**
 * Day-by-hour active minutes for the intraday heatmap, from the
 * hourly_minutes_by_category matrix the API already returns.
 */
export function toIntradayActivityMatrix(
  rollups: readonly TractiveDailySummary[],
): IntradayActivityMatrix {
  const rows = [...rollups]
    .sort((first, second) => first.date.localeCompare(second.date))
    .map((rollup) => ({
      date: rollup.date,
      dayLabel: formatMonthDay(rollup.date),
      hourlyActiveMinutes: Array.from(
        { length: 24 },
        (_, hour) => rollup.hourly_minutes_by_category[String(hour)]?.active ?? 0,
      ),
      lowCoverage: !hasCleanCoverage(rollup),
    }));
  const maxActiveMinutes = Math.max(0, ...rows.flatMap((row) => row.hourlyActiveMinutes));
  return { rows, maxActiveMinutes };
}

// TODO: replace with breed/age/size-aware norms (see specs/006-tractive-integration.md
// follow-ups + the planned breed_norms table). For now we use generic adult-dog
// safe ranges so the chip is at least directionally honest.
export const VITAL_RANGES = {
  restingHeartRateBpm: { low: 50, high: 130 },
  restingRespiratoryRpm: { low: 8, high: 40 },
} as const;

export type VitalsStatus = {
  label: string;
  tone: "positive" | "caution" | "neutral";
};

function computeVitalsStatus(today: {
  heart_rate_record_mean: number | null;
  respiratory_rate_record_mean: number | null;
}): VitalsStatus {
  const checks: Array<{ value: number | null; range: { low: number; high: number } }> = [
    { value: today.heart_rate_record_mean, range: VITAL_RANGES.restingHeartRateBpm },
    { value: today.respiratory_rate_record_mean, range: VITAL_RANGES.restingRespiratoryRpm },
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
  goalBaseline?: readonly TractiveDailySummary[],
): TodayPanelData | undefined {
  if (rollups.length === 0) return undefined;

  const sorted = [...rollups].sort((a, b) => a.date.localeCompare(b.date));
  const today = sorted[sorted.length - 1];
  const preceding = sorted.slice(0, -1);

  const activeBaseline = meanOfPreceding(preceding, (rollup) => rollup.minutes_active);
  const sleepBaseline = meanOfPreceding(preceding, totalSleepMinutes);
  const distanceBaseline = meanOfPreceding(preceding, (rollup) => rollup.gps_distance_km);
  const calmBaseline = meanOfPreceding(preceding, (rollup) => rollup.minutes_low_intensity);

  const activityGoal = computePersonalActivityGoal(goalBaseline ?? preceding);

  // Raw (unclamped) percent — the ActivityRing component caps the visual fill
  // and shifts color when the goal is exceeded.
  const activityPercent = roundedPercent((today.minutes_active / activityGoal) * 100);
  const sublabel =
    activityPercent <= 100
      ? `${activityPercent}% of ${activityGoal}min goal`
      : `${activityPercent}% — goal smashed`;

  const totalSleepToday = totalSleepMinutes(today);
  const sleepSplitCopy = `${formatHoursMinutes(today.minutes_night_sleep)} night · ${formatHoursMinutes(today.minutes_day_sleep)} naps`;

  return {
    latestDate: today.date,
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
        value:
          today.heart_rate_record_mean === null
            ? "—"
            : String(Math.round(today.heart_rate_record_mean)),
        unit: "bpm",
      },
      {
        label: "Respiratory",
        value:
          today.respiratory_rate_record_mean === null
            ? "—"
            : String(Math.round(today.respiratory_rate_record_mean)),
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
    activityGoal,
    coverageNote: toCoverageNote(today),
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

export function toLatestDayEyebrow(latestDate: string | undefined, todayLabel: string): string {
  if (latestDate === undefined) return `Today — ${todayLabel}`;
  return `Latest tracker day — ${formatFullDate(latestDate)}`;
}
