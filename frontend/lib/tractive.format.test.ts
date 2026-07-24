import { describe, expect, it } from "vitest";
import {
  COVERAGE_CAVEAT_THRESHOLD_MINUTES,
  DAILY_ACTIVE_TARGET_MINUTES,
  MINIMUM_RECORDS_FOR_DAILY_VITAL,
  computePersonalActivityGoal,
  toCoverageNote,
  toIntradayActivityMatrix,
  toOutingsCardData,
  toRespiratoryNightDayComparison,
  toSleepQualityData,
  toSleepSplitBars,
  toTodayPanelData,
  toVitalsTrends,
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
  function cleanDays(activeMinutes: number[]): TractiveDailySummary[] {
    return activeMinutes.map((minutes, index) =>
      makeRollup({
        date: `2024-05-${String(index + 1).padStart(2, "0")}`,
        minutes_active: minutes,
      }),
    );
  }

  it("falls back to the generic target with fewer than five clean days", () => {
    expect(computePersonalActivityGoal([])).toBe(DAILY_ACTIVE_TARGET_MINUTES);
    expect(computePersonalActivityGoal(cleanDays([200, 250, 300, 280]))).toBe(
      DAILY_ACTIVE_TARGET_MINUTES,
    );
  });

  it("returns the median of clean preceding days", () => {
    expect(computePersonalActivityGoal(cleanDays([200, 250, 270, 300, 400]))).toBe(270);
  });

  it("averages the middle pair for an even count of clean days", () => {
    expect(computePersonalActivityGoal(cleanDays([200, 250, 270, 300, 400, 410]))).toBe(285);
  });

  it("excludes low-coverage days from the median", () => {
    const days = cleanDays([200, 250, 270, 300, 400]);
    days.push(
      makeRollup({
        date: "2024-05-06",
        minutes_active: 10,
        minutes_no_signal: COVERAGE_CAVEAT_THRESHOLD_MINUTES + 1,
      }),
    );
    expect(computePersonalActivityGoal(days)).toBe(270);
  });

  it("falls back when low-coverage days push the clean count under five", () => {
    const days = cleanDays([200, 250, 270, 300]);
    days.push(
      makeRollup({
        date: "2024-05-05",
        minutes_active: 400,
        minutes_no_signal: COVERAGE_CAVEAT_THRESHOLD_MINUTES + 1,
      }),
    );
    expect(computePersonalActivityGoal(days)).toBe(DAILY_ACTIVE_TARGET_MINUTES);
  });
});

describe("toCoverageNote", () => {
  it("returns undefined for a clean day", () => {
    expect(toCoverageNote(makeRollup({ minutes_no_signal: 0 }))).toBeUndefined();
    expect(
      toCoverageNote(makeRollup({ minutes_no_signal: COVERAGE_CAVEAT_THRESHOLD_MINUTES })),
    ).toBeUndefined();
  });

  it("describes the missing time for a low-coverage day", () => {
    const note = toCoverageNote(makeRollup({ minutes_no_signal: 619 }));
    expect(note).toBe(
      "10h 19m of this day has no activity data, so totals are a floor, not the full picture.",
    );
  });
});

describe("toIntradayActivityMatrix", () => {
  it("returns an empty matrix for no rollups", () => {
    expect(toIntradayActivityMatrix([])).toEqual({ rows: [], maxActiveMinutes: 0 });
  });

  it("builds 24 hour slots per day, defaulting missing hours to zero", () => {
    const { rows, maxActiveMinutes } = toIntradayActivityMatrix([
      makeRollup({
        date: "2024-05-15",
        hourly_minutes_by_category: {
          "8": { active: 40.5, moderate: 3 },
          "18": { active: 12 },
        },
      }),
    ]);
    expect(rows).toHaveLength(1);
    expect(rows[0].hourlyActiveMinutes).toHaveLength(24);
    expect(rows[0].hourlyActiveMinutes[8]).toBe(40.5);
    expect(rows[0].hourlyActiveMinutes[18]).toBe(12);
    expect(rows[0].hourlyActiveMinutes[0]).toBe(0);
    expect(maxActiveMinutes).toBe(40.5);
  });

  it("sorts rows by date and flags low-coverage days", () => {
    const { rows } = toIntradayActivityMatrix([
      makeRollup({
        date: "2024-05-16",
        minutes_no_signal: COVERAGE_CAVEAT_THRESHOLD_MINUTES + 1,
      }),
      makeRollup({ date: "2024-05-15" }),
    ]);
    expect(rows.map((row) => row.date)).toEqual(["2024-05-15", "2024-05-16"]);
    expect(rows[0].lowCoverage).toBe(false);
    expect(rows[1].lowCoverage).toBe(true);
    expect(rows[0].dayLabel).toBe("May 15");
  });
});

describe("toTodayPanelData personal goal and coverage", () => {
  it("uses the personal median goal once five clean preceding days exist", () => {
    const preceding = [200, 250, 270, 300, 400].map((minutes, index) =>
      makeRollup({ date: `2024-05-${String(index + 10)}`, minutes_active: minutes }),
    );
    const result = toTodayPanelData([
      ...preceding,
      makeRollup({ date: "2024-05-20", minutes_active: 270 }),
    ]);
    expect(result?.activityGoal).toBe(270);
    expect(result?.activityPercent).toBe(100);
    expect(result?.activitySublabel).toBe("100% of 270min goal");
  });

  it("exposes a coverage note when today has a large no-signal gap", () => {
    const result = toTodayPanelData([
      makeRollup({ date: "2024-05-15" }),
      makeRollup({ date: "2024-05-16", minutes_no_signal: 619 }),
    ]);
    expect(result?.coverageNote).toMatch(/10h 19m of this day has no activity data/);
  });

  it("omits the coverage note on clean days", () => {
    const result = toTodayPanelData([makeRollup({ date: "2024-05-16" })]);
    expect(result?.coverageNote).toBeUndefined();
  });
});

describe("toVitalsTrends", () => {
  function vitalDay(
    date: string,
    recordMean: number | null,
    recordCount: number,
  ): TractiveDailySummary {
    return makeRollup({
      date,
      heart_rate_record_mean: recordMean,
      heart_rate_record_count: recordCount,
    });
  }

  it("plots only days with enough accepted records", () => {
    const { heartRate } = toVitalsTrends([
      vitalDay("2024-05-15", 62, 25),
      vitalDay("2024-05-16", 60, 5),
      vitalDay("2024-05-17", 66, 12),
    ]);
    expect(heartRate.values).toEqual([62, 66]);
    expect(heartRate.dates).toEqual(["May 15", "May 17"]);
    expect(heartRate.measuredDayCount).toBe(3);
    expect(heartRate.suppressedDayCount).toBe(1);
    expect(heartRate.latest).toBe(66);
  });

  it("skips days without any accepted records entirely", () => {
    const { heartRate } = toVitalsTrends([
      vitalDay("2024-05-15", 62, 25),
      vitalDay("2024-05-16", null, 0),
    ]);
    expect(heartRate.measuredDayCount).toBe(1);
    expect(heartRate.suppressedDayCount).toBe(0);
  });

  it("omits the typical range until five plotted days exist", () => {
    const fourDays = ["2024-05-15", "2024-05-16", "2024-05-17", "2024-05-18"].map((date, index) =>
      vitalDay(date, 60 + index, 20),
    );
    expect(toVitalsTrends(fourDays).heartRate.typicalRange).toBeUndefined();

    const fiveDays = [...fourDays, vitalDay("2024-05-19", 70, 20)];
    const { heartRate } = toVitalsTrends(fiveDays);
    expect(heartRate.typicalRange).toEqual({ low: 61, high: 63 });
  });

  it("sorts by date before building the series", () => {
    const { heartRate } = toVitalsTrends([
      vitalDay("2024-05-17", 66, 12),
      vitalDay("2024-05-15", 62, 25),
    ]);
    expect(heartRate.values).toEqual([62, 66]);
  });

  it("builds the respiratory series from the respiratory record fields", () => {
    const { respiratoryRate } = toVitalsTrends([
      makeRollup({
        date: "2024-05-15",
        respiratory_rate_record_mean: 17.5,
        respiratory_rate_record_count: 15,
      }),
      makeRollup({
        date: "2024-05-16",
        respiratory_rate_record_mean: 19,
        respiratory_rate_record_count: 11,
      }),
    ]);
    expect(respiratoryRate.values).toEqual([17.5, 19]);
    expect(respiratoryRate.latest).toBe(19);
  });
});

describe("toRespiratoryNightDayComparison", () => {
  function nightDayRollup(
    date: string,
    nightMean: number,
    nightCount: number,
    dayMean: number,
    dayCount: number,
  ): TractiveDailySummary {
    return makeRollup({
      date,
      respiratory_rate_night_record_mean: nightMean,
      respiratory_rate_night_record_count: nightCount,
      respiratory_rate_day_record_mean: dayMean,
      respiratory_rate_day_record_count: dayCount,
    });
  }

  it("returns undefined when either bucket lacks enough records", () => {
    expect(
      toRespiratoryNightDayComparison([nightDayRollup("2024-05-15", 16, 9, 21, 30)]),
    ).toBeUndefined();
    expect(
      toRespiratoryNightDayComparison([nightDayRollup("2024-05-15", 16, 30, 21, 9)]),
    ).toBeUndefined();
    expect(toRespiratoryNightDayComparison([])).toBeUndefined();
  });

  it("computes record-weighted means across the range", () => {
    const comparison = toRespiratoryNightDayComparison([
      nightDayRollup("2024-05-15", 16, 10, 20, 10),
      nightDayRollup("2024-05-16", 18, 30, 24, 10),
    ]);
    expect(comparison).toEqual({
      nightMean: 17.5,
      dayMean: 22,
      nightRecordCount: 40,
      dayRecordCount: 20,
    });
  });
});

describe("clean-coverage boundary at exactly the threshold", () => {
  it("treats a day at exactly the threshold as clean for the goal", () => {
    const days = [200, 250, 270, 300].map((minutes, index) =>
      makeRollup({ date: `2024-05-0${index + 1}`, minutes_active: minutes }),
    );
    days.push(
      makeRollup({
        date: "2024-05-05",
        minutes_active: 400,
        minutes_no_signal: COVERAGE_CAVEAT_THRESHOLD_MINUTES,
      }),
    );
    expect(computePersonalActivityGoal(days)).toBe(270);
  });

  it("does not flag a day at exactly the threshold in the matrix", () => {
    const { rows } = toIntradayActivityMatrix([
      makeRollup({ minutes_no_signal: COVERAGE_CAVEAT_THRESHOLD_MINUTES }),
    ]);
    expect(rows[0].lowCoverage).toBe(false);
  });
});

describe("toVitalsTrends minimum-records boundary", () => {
  it("plots a day with exactly the minimum record count", () => {
    const { heartRate } = toVitalsTrends([
      makeRollup({
        date: "2024-05-15",
        heart_rate_record_mean: 62,
        heart_rate_record_count: MINIMUM_RECORDS_FOR_DAILY_VITAL,
      }),
      makeRollup({
        date: "2024-05-16",
        heart_rate_record_mean: 64,
        heart_rate_record_count: MINIMUM_RECORDS_FOR_DAILY_VITAL - 1,
      }),
    ]);
    expect(heartRate.values).toEqual([62]);
    expect(heartRate.suppressedDayCount).toBe(1);
  });

  it("returns defined empty series for an empty rollup list", () => {
    const trends = toVitalsTrends([]);
    expect(trends.heartRate.values).toEqual([]);
    expect(trends.heartRate.latest).toBeNull();
    expect(trends.heartRate.typicalRange).toBeUndefined();
    expect(trends.respiratoryNightDay).toBeUndefined();
  });
});

describe("toOutingsCardData", () => {
  it("returns undefined for empty rollups", () => {
    expect(toOutingsCardData([])).toBeUndefined();
  });

  it("builds latest-day rows with floor-framed labels", () => {
    const data = toOutingsCardData([
      makeRollup({ date: "2024-05-14" }),
      makeRollup({
        date: "2024-05-15",
        outings_count: 2,
        outings_total_minutes: 57,
        outings: [
          {
            started_at: "2024-05-15T04:40:00+00:00",
            ended_at: "2024-05-15T05:12:00+00:00",
            duration_minutes: 32,
            max_distance_meters: 820,
            fix_count: 6,
          },
          {
            started_at: "2024-05-15T15:05:00+00:00",
            ended_at: "2024-05-15T15:30:00+00:00",
            duration_minutes: 25,
            max_distance_meters: 460,
            fix_count: 5,
          },
        ],
      }),
    ]);
    expect(data?.latestDayLabel).toBe("May 15");
    expect(data?.latestCount).toBe(2);
    expect(data?.latestRows).toHaveLength(2);
    expect(data?.latestRows[0].durationLabel).toBe("at least 32 min");
    expect(data?.latestRows[0].distanceLabel).toBe("up to 0.8 km away");
    expect(data?.latestRows[0].startLabel).toMatch(/^\d{2}:\d{2}$/);
  });

  it("averages the floor count across the range", () => {
    const data = toOutingsCardData([
      makeRollup({ date: "2024-05-14", outings_count: 3 }),
      makeRollup({ date: "2024-05-15", outings_count: 2 }),
    ]);
    expect(data?.rangeDailyAverage).toBe(2.5);
    expect(data?.daysInRange).toBe(2);
  });

  it("omits the range average for a single day", () => {
    const data = toOutingsCardData([makeRollup({ date: "2024-05-15" })]);
    expect(data?.rangeDailyAverage).toBeNull();
  });

  it("handles unparseable timestamps without crashing", () => {
    const data = toOutingsCardData([
      makeRollup({
        date: "2024-05-15",
        outings_count: 1,
        outings: [
          {
            started_at: "not-a-date",
            ended_at: "not-a-date",
            duration_minutes: 10,
            max_distance_meters: 200,
            fix_count: 3,
          },
        ],
      }),
    ]);
    expect(data?.latestRows[0].startLabel).toBe("--:--");
  });
});

describe("toOutingsCardData review follow-ups", () => {
  it("picks the max date as latest even from unsorted input", () => {
    const data = toOutingsCardData([
      makeRollup({ date: "2024-05-16", outings_count: 1 }),
      makeRollup({ date: "2024-05-14", outings_count: 4 }),
      makeRollup({ date: "2024-05-15", outings_count: 2 }),
    ]);
    expect(data?.latestDayLabel).toBe("May 16");
    expect(data?.latestCount).toBe(1);
  });

  it("counts zero-outing days in the range average denominator", () => {
    const data = toOutingsCardData([
      makeRollup({ date: "2024-05-14", outings_count: 4 }),
      makeRollup({ date: "2024-05-15", outings_count: 0 }),
      makeRollup({ date: "2024-05-16", outings_count: 2 }),
    ]);
    expect(data?.rangeDailyAverage).toBe(2);
    expect(data?.daysInRange).toBe(3);
  });

  it("rounds distances half-up at half-decimal kilometre boundaries", () => {
    const data = toOutingsCardData([
      makeRollup({
        date: "2024-05-15",
        outings_count: 2,
        outings: [
          {
            started_at: "2024-05-15T05:00:00Z",
            ended_at: "2024-05-15T05:20:00Z",
            duration_minutes: 20,
            max_distance_meters: 850,
            fix_count: 4,
          },
          {
            started_at: "2024-05-15T15:00:00Z",
            ended_at: "2024-05-15T15:20:00Z",
            duration_minutes: 20,
            max_distance_meters: 460,
            fix_count: 4,
          },
        ],
      }),
    ]);
    expect(data?.latestRows[0].distanceLabel).toBe("up to 0.9 km away");
    expect(data?.latestRows[1].distanceLabel).toBe("up to 0.5 km away");
  });
});

describe("toSleepQualityData", () => {
  it("returns undefined for empty rollups", () => {
    expect(toSleepQualityData([])).toBeUndefined();
  });

  it("builds the sorted longest-bout series with range averages", () => {
    const data = toSleepQualityData([
      makeRollup({
        date: "2024-05-16",
        sleep_longest_bout_minutes: 420,
        sleep_bout_count: 6,
        sleep_fragmentation_index: 8,
      }),
      makeRollup({
        date: "2024-05-15",
        sleep_longest_bout_minutes: 375,
        sleep_bout_count: 9,
        sleep_fragmentation_index: 12,
      }),
    ]);
    expect(data?.values).toEqual([375, 420]);
    expect(data?.dates).toEqual(["May 15", "May 16"]);
    expect(data?.latestLongestBoutMinutes).toBe(420);
    expect(data?.averageBoutCount).toBe(7.5);
    expect(data?.averageFragmentationIndex).toBe(10);
  });

  it("skips null fragmentation values in the average", () => {
    const data = toSleepQualityData([
      makeRollup({
        date: "2024-05-15",
        sleep_fragmentation_index: 8,
      }),
      makeRollup({ date: "2024-05-16", sleep_fragmentation_index: null }),
    ]);
    expect(data?.averageFragmentationIndex).toBe(8);
  });

  it("reports null fragmentation when no day has a value", () => {
    const data = toSleepQualityData([
      makeRollup({ date: "2024-05-15", sleep_fragmentation_index: null }),
    ]);
    expect(data?.averageFragmentationIndex).toBeNull();
    expect(data?.averageBoutCount).toBe(0);
  });

  it("counts low-coverage days", () => {
    const data = toSleepQualityData([
      makeRollup({ date: "2024-05-15" }),
      makeRollup({
        date: "2024-05-16",
        minutes_no_signal: COVERAGE_CAVEAT_THRESHOLD_MINUTES + 1,
      }),
    ]);
    expect(data?.lowCoverageDayCount).toBe(1);
  });
});
