import { describe, expect, it } from "vitest";
import {
  DAILY_ACTIVE_TARGET_MINUTES,
  computePersonalActivityGoal,
  toOutingsCardData,
  toSleepQualityData,
  toLatestDayEyebrow,
  toSleepSplitBars,
  toTodayPanelData,
} from "./tractive.format";
import type { TractiveDailySummary } from "./tractive";

function makeRollup(overrides: Partial<TractiveDailySummary>): TractiveDailySummary {
  return {
    date: "2024-05-15",
    minutes_active: 0,
    minutes_low_intensity: 0,
    minutes_moderate: 0,
    minutes_night_sleep: 0,
    minutes_day_sleep: 0,
    minutes_no_signal: 0,
    hourly_minutes_by_category: {},
    heart_rate_mean: null,
    respiratory_rate_mean: null,
    heart_rate_record_count: 0,
    heart_rate_record_mean: null,
    heart_rate_ci95_half_width: null,
    respiratory_rate_record_count: 0,
    respiratory_rate_record_mean: null,
    respiratory_rate_ci95_half_width: null,
    respiratory_rate_night_record_count: 0,
    respiratory_rate_night_record_mean: null,
    respiratory_rate_day_record_count: 0,
    respiratory_rate_day_record_mean: null,
    sleep_longest_bout_minutes: 0,
    sleep_bout_count: 0,
    sleep_fragmentation_index: null,
    outings_count: 0,
    outings_total_minutes: 0,
    outings: [],
    gps_distance_km: 0,
    ...overrides,
  };
}

describe("toTodayPanelData", () => {
  it("returns undefined for empty input", () => {
    expect(toTodayPanelData([])).toBeUndefined();
  });

  it("uses the most recent day as 'today'", () => {
    const result = toTodayPanelData([
      makeRollup({ date: "2024-05-14", minutes_active: 30 }),
      makeRollup({ date: "2024-05-16", minutes_active: DAILY_ACTIVE_TARGET_MINUTES }),
      makeRollup({ date: "2024-05-15", minutes_active: 60 }),
    ]);
    expect(result?.activityLabel).toBe(
      `${Math.floor(DAILY_ACTIVE_TARGET_MINUTES / 60)}h ${String(DAILY_ACTIVE_TARGET_MINUTES % 60).padStart(2, "0")}m`,
    );
    expect(result?.activityPercent).toBe(100);
  });

  it("derives weekday labels from the actual dates in chronological order", () => {
    const result = toTodayPanelData([
      makeRollup({ date: "2024-05-16" }),
      makeRollup({ date: "2024-05-14" }),
      makeRollup({ date: "2024-05-15" }),
    ]);
    // May 14-16, 2024 are Tue, Wed, Thu.
    expect(result?.weekDates).toEqual(["May 14", "May 15", "May 16"]);
    expect(result?.weekDays).toEqual(["Tu", "We", "Th"]);
  });

  it("returns raw (unclamped) activity percent so the ring can render an overage state", () => {
    const high = toTodayPanelData([
      makeRollup({ minutes_active: DAILY_ACTIVE_TARGET_MINUTES * 5 }),
    ]);
    expect(high?.activityPercent).toBe(500);
    expect(high?.activitySublabel).toMatch(/goal smashed/i);

    const low = toTodayPanelData([makeRollup({ minutes_active: 0 })]);
    expect(low?.activityPercent).toBe(0);
    expect(low?.activitySublabel).toBe(`0% of ${DAILY_ACTIVE_TARGET_MINUTES}min goal`);
  });

  it("uses the standard sublabel when at or under 100%", () => {
    const result = toTodayPanelData([makeRollup({ minutes_active: DAILY_ACTIVE_TARGET_MINUTES })]);
    expect(result?.activityPercent).toBe(100);
    expect(result?.activitySublabel).toBe(`100% of ${DAILY_ACTIVE_TARGET_MINUTES}min goal`);
  });

  it("formats minutes under 60 without an hours component", () => {
    const result = toTodayPanelData([makeRollup({ minutes_active: 45 })]);
    expect(result?.activityLabel).toBe("45m");
  });

  it("produces the six standard metric tiles in order", () => {
    const result = toTodayPanelData([
      makeRollup({
        minutes_active: 60,
        minutes_low_intensity: 200,
        minutes_night_sleep: 400,
        minutes_day_sleep: 80,
        heart_rate_mean: 62,
        respiratory_rate_mean: 17,
        gps_distance_km: 3.4,
      }),
    ]);
    expect(result?.metrics.map((metric) => metric.label)).toEqual([
      "Active",
      "Sleep",
      "Resting HR",
      "Respiratory",
      "Distance",
      "Calm time",
    ]);
  });

  it("always shows the night/day split in the Sleep tile delta", () => {
    const single = toTodayPanelData([
      makeRollup({ minutes_night_sleep: 420, minutes_day_sleep: 90 }),
    ]);
    expect(single?.metrics.find((metric) => metric.label === "Sleep")?.value).toBe("8h 30m");
    expect(single?.metrics.find((metric) => metric.label === "Sleep")?.delta).toBe(
      "7h 00m night · 1h 30m naps",
    );

    // Even with prior days available, the split (not the vs-avg delta) wins
    // — the trend chart is where the vs-avg story is told.
    const withBaseline = toTodayPanelData([
      makeRollup({ date: "2024-05-13", minutes_night_sleep: 600, minutes_day_sleep: 100 }),
      makeRollup({ date: "2024-05-14", minutes_night_sleep: 580, minutes_day_sleep: 80 }),
      makeRollup({ date: "2024-05-15", minutes_night_sleep: 420, minutes_day_sleep: 90 }),
    ]);
    expect(withBaseline?.metrics.find((metric) => metric.label === "Sleep")?.delta).toBe(
      "7h 00m night · 1h 30m naps",
    );
  });

  it("shows em-dash for missing vitals", () => {
    const result = toTodayPanelData([
      makeRollup({ heart_rate_mean: null, respiratory_rate_mean: null }),
    ]);
    expect(result?.metrics.find((metric) => metric.label === "Resting HR")?.value).toBe("—");
    expect(result?.metrics.find((metric) => metric.label === "Respiratory")?.value).toBe("—");
  });

  it("rounds vitals to nearest integer", () => {
    const result = toTodayPanelData([
      makeRollup({ heart_rate_mean: 62.6, respiratory_rate_mean: 18.4 }),
    ]);
    expect(result?.metrics.find((metric) => metric.label === "Resting HR")?.value).toBe("63");
    expect(result?.metrics.find((metric) => metric.label === "Respiratory")?.value).toBe("18");
  });

  it("returns weekMinutes arrays aligned with sorted dates", () => {
    const result = toTodayPanelData([
      makeRollup({
        date: "2024-05-15",
        minutes_active: 30,
        minutes_night_sleep: 400,
        minutes_day_sleep: 50,
      }),
      makeRollup({
        date: "2024-05-16",
        minutes_active: 60,
        minutes_night_sleep: 500,
        minutes_day_sleep: 60,
      }),
    ]);
    expect(result?.activityWeekMinutes).toEqual([30, 60]);
    expect(result?.sleepWeekMinutes).toEqual([450, 560]);
    expect(result?.weekDates).toEqual(["May 15", "May 16"]);
  });

  it("exposes activityGoal and rolling baseline means for chart overlays", () => {
    const result = toTodayPanelData([
      makeRollup({ date: "2024-05-13", minutes_active: 60, minutes_night_sleep: 600 }),
      makeRollup({ date: "2024-05-14", minutes_active: 80, minutes_night_sleep: 700 }),
      makeRollup({ date: "2024-05-15", minutes_active: 100, minutes_night_sleep: 500 }),
    ]);
    expect(result?.activityGoal).toBe(DAILY_ACTIVE_TARGET_MINUTES);
    expect(result?.activityWeekMean).toBe(70); // (60+80)/2
    expect(result?.sleepWeekMean).toBe(650); // (600+700)/2 (only night since day=0)
  });

  it("computes deltas vs the rolling preceding mean", () => {
    const result = toTodayPanelData([
      makeRollup({ date: "2024-05-13", minutes_active: 60, gps_distance_km: 2.0 }),
      makeRollup({ date: "2024-05-14", minutes_active: 80, gps_distance_km: 3.0 }),
      makeRollup({ date: "2024-05-15", minutes_active: 100, gps_distance_km: 4.5 }),
    ]);
    const active = result?.metrics.find((metric) => metric.label === "Active");
    const distance = result?.metrics.find((metric) => metric.label === "Distance");
    // active baseline = 70 → today 100 → +30
    expect(active?.delta).toBe("↑ 30 min vs avg");
    // distance baseline = 2.5 → today 4.5 → +2.0
    expect(distance?.delta).toBe("↑ 2.0 km vs avg");
  });

  it("omits baseline mean fields when only one day exists", () => {
    const result = toTodayPanelData([makeRollup({ minutes_active: 60 })]);
    expect(result?.activityWeekMean).toBeUndefined();
    expect(result?.sleepWeekMean).toBeUndefined();
  });

  it("reports 'All vitals normal' when HR and RR are inside generic safe ranges", () => {
    const result = toTodayPanelData([
      makeRollup({ heart_rate_mean: 70, respiratory_rate_mean: 20 }),
    ]);
    expect(result?.vitalsStatus).toEqual({ label: "All vitals normal", tone: "positive" });
  });

  it("flags caution when any vital is outside generic safe ranges", () => {
    const lowHr = toTodayPanelData([
      makeRollup({ heart_rate_mean: 30, respiratory_rate_mean: 20 }),
    ]);
    expect(lowHr?.vitalsStatus).toEqual({ label: "Vitals out of range", tone: "caution" });

    const highRr = toTodayPanelData([
      makeRollup({ heart_rate_mean: 70, respiratory_rate_mean: 90 }),
    ]);
    expect(highRr?.vitalsStatus).toEqual({ label: "Vitals out of range", tone: "caution" });
  });

  it("reports 'No vitals yet' when neither HR nor RR is measured", () => {
    const result = toTodayPanelData([
      makeRollup({ heart_rate_mean: null, respiratory_rate_mean: null }),
    ]);
    expect(result?.vitalsStatus).toEqual({ label: "No vitals yet", tone: "neutral" });
  });
});

describe("toSleepSplitBars", () => {
  it("returns an empty array for no rollups", () => {
    expect(toSleepSplitBars([])).toEqual([]);
  });

  it("produces one bar per day with night/day minutes preserved", () => {
    const bars = toSleepSplitBars([
      makeRollup({
        date: "2024-05-16",
        minutes_night_sleep: 500,
        minutes_day_sleep: 60,
      }),
      makeRollup({
        date: "2024-05-15",
        minutes_night_sleep: 420,
        minutes_day_sleep: 90,
      }),
    ]);
    // Sorted ascending by date.
    expect(bars.map((bar) => bar.date)).toEqual(["2024-05-15", "2024-05-16"]);
    expect(bars[0]).toEqual({
      date: "2024-05-15",
      dayLabel: "May 15",
      nightMinutes: 420,
      dayMinutes: 90,
    });
    expect(bars[1]).toEqual({
      date: "2024-05-16",
      dayLabel: "May 16",
      nightMinutes: 500,
      dayMinutes: 60,
    });
  });
});

describe("computePersonalActivityGoal", () => {
  it("falls back to the generic target when the median is zero", () => {
    const cratRestDays = Array.from({ length: 6 }, (_unused, index) =>
      makeRollup({ date: `2024-05-0${index + 1}`, minutes_active: 0 }),
    );

    expect(computePersonalActivityGoal(cratRestDays)).toBe(DAILY_ACTIVE_TARGET_MINUTES);
  });

  it("uses the personal median once there is enough clean history", () => {
    const days = Array.from({ length: 6 }, (_unused, index) =>
      makeRollup({ date: `2024-05-0${index + 1}`, minutes_active: 90 }),
    );

    expect(computePersonalActivityGoal(days)).toBe(90);
  });
});

describe("toSleepQualityData", () => {
  it("omits days where continuity was never derived rather than plotting them as zero", () => {
    const result = toSleepQualityData([
      makeRollup({ date: "2024-05-14", sleep_longest_bout_minutes: 300, sleep_bout_count: 4 }),
      makeRollup({
        date: "2024-05-15",
        sleep_longest_bout_minutes: null,
        sleep_bout_count: null,
      }),
    ]);

    expect(result?.values).toEqual([300]);
    expect(result?.unmeasuredDayCount).toBe(1);
    expect(result?.latestLongestBoutMinutes).toBe(300);
    expect(result?.averageBoutCount).toBe(4);
  });

  it("returns undefined when no day has a derived bout", () => {
    const result = toSleepQualityData([
      makeRollup({ date: "2024-05-15", sleep_longest_bout_minutes: null }),
    ]);

    expect(result).toBeUndefined();
  });
});

describe("toOutingsCardData", () => {
  it("excludes underived days from the range average", () => {
    const result = toOutingsCardData([
      makeRollup({ date: "2024-05-14", outings_count: 3 }),
      makeRollup({ date: "2024-05-15", outings_count: null }),
      makeRollup({ date: "2024-05-16", outings_count: 1 }),
    ]);

    expect(result?.daysInRange).toBe(2);
    expect(result?.rangeDailyAverage).toBe(2);
  });
});

describe("toLatestDayEyebrow", () => {
  it("names the day the figures come from, not the calendar date", () => {
    expect(toLatestDayEyebrow("2024-07-15", "Sat, Aug 1")).toBe(
      "Latest tracker day — Mon, Jul 15",
    );
  });

  it("falls back to the calendar date when there is no tracker data", () => {
    expect(toLatestDayEyebrow(undefined, "Sat, Aug 1")).toBe("Today — Sat, Aug 1");
  });
});
