import { describe, expect, it } from "vitest";
import { formatMonthDay, formatWeekday } from "./date";

describe("formatMonthDay", () => {
  it("formats an ISO date as a short month and day", () => {
    expect(formatMonthDay("2026-07-15")).toBe("Jul 15");
  });

  it("interprets the date in UTC regardless of local timezone", () => {
    expect(formatMonthDay("2026-01-01")).toBe("Jan 1");
  });

  it("returns the input unchanged when it is not a valid ISO date", () => {
    expect(formatMonthDay("not-a-date")).toBe("not-a-date");
    expect(formatMonthDay("2026-00-10")).toBe("2026-00-10");
  });
});

describe("formatWeekday", () => {
  it("returns the correct two-letter weekday for a known date", () => {
    // 2026-07-15 is a Wednesday.
    expect(formatWeekday("2026-07-15")).toBe("We");
  });

  it("maps a full week of dates to the right abbreviations", () => {
    expect(formatWeekday("2026-07-09")).toBe("Th");
    expect(formatWeekday("2026-07-10")).toBe("Fr");
    expect(formatWeekday("2026-07-11")).toBe("Sa");
    expect(formatWeekday("2026-07-12")).toBe("Su");
    expect(formatWeekday("2026-07-13")).toBe("Mo");
    expect(formatWeekday("2026-07-14")).toBe("Tu");
    expect(formatWeekday("2026-07-15")).toBe("We");
  });

  it("returns the input unchanged when it is not a valid ISO date", () => {
    expect(formatWeekday("not-a-date")).toBe("not-a-date");
  });
});
