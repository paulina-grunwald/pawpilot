import { afterEach, describe, expect, it, vi } from "vitest";
import type { JournalEntryRead } from "./journal.schemas";
import {
  fetchPetWeightSeries,
  formatWeightKg,
  meanWeightGrams,
  toWeightSeries,
} from "./weight";

const { listJournalEntriesMock } = vi.hoisted(() => ({
  listJournalEntriesMock: vi.fn(),
}));

vi.mock("./journal", () => ({
  listJournalEntries: (...args: unknown[]) => listJournalEntriesMock(...args),
}));

function makeWeightEntry(
  occurredAt: string,
  weightGrams: number,
  overrides: Partial<JournalEntryRead> = {},
): JournalEntryRead {
  return {
    id: `entry-${occurredAt}`,
    pet_id: "pet-1",
    entry_type: "weight",
    payload: { entry_type: "weight", weight_grams: weightGrams, source: "home_scale" },
    occurred_at: occurredAt,
    note: null,
    tags: [],
    is_concern: false,
    photo_path: null,
    photo_url: null,
    created_at: occurredAt,
    updated_at: occurredAt,
    ...overrides,
  };
}

afterEach(() => {
  listJournalEntriesMock.mockReset();
});

describe("toWeightSeries", () => {
  it("maps weight entries into an ascending series of kg points", () => {
    const series = toWeightSeries([
      makeWeightEntry("2024-05-23T08:00:00Z", 27600),
      makeWeightEntry("2024-05-20T08:00:00Z", 27400),
    ]);
    expect(series).toEqual([
      { date: "2024-05-20", label: "May 20", weightGrams: 27400 },
      { date: "2024-05-23", label: "May 23", weightGrams: 27600 },
    ]);
  });

  it("ignores non-weight entries", () => {
    const nonWeight: JournalEntryRead = {
      ...makeWeightEntry("2024-05-21T08:00:00Z", 27500),
      entry_type: "mood",
      payload: { entry_type: "mood", score: 4 },
    };
    const series = toWeightSeries([nonWeight, makeWeightEntry("2024-05-22T08:00:00Z", 27500)]);
    expect(series).toHaveLength(1);
    expect(series[0]?.date).toBe("2024-05-22");
  });

  it("keeps only the latest reading per calendar day", () => {
    const series = toWeightSeries([
      makeWeightEntry("2024-05-22T07:00:00Z", 27300),
      makeWeightEntry("2024-05-22T19:00:00Z", 27700),
    ]);
    expect(series).toHaveLength(1);
    expect(series[0]?.weightGrams).toBe(27700);
  });

  it("returns an empty series when there are no entries", () => {
    expect(toWeightSeries([])).toEqual([]);
  });
});

describe("meanWeightGrams", () => {
  it("averages the readings", () => {
    expect(
      meanWeightGrams([
        { date: "2024-05-20", label: "May 20", weightGrams: 27000 },
        { date: "2024-05-21", label: "May 21", weightGrams: 28000 },
      ]),
    ).toBe(27500);
  });

  it("returns null for an empty series", () => {
    expect(meanWeightGrams([])).toBeNull();
  });
});

describe("formatWeightKg", () => {
  it("formats grams as one-decimal kilograms", () => {
    expect(formatWeightKg(27600)).toBe("27.6 kg");
    expect(formatWeightKg(30000)).toBe("30.0 kg");
  });
});

describe("fetchPetWeightSeries", () => {
  it("requests weight entries for the trailing window and maps them", async () => {
    listJournalEntriesMock.mockResolvedValue({
      items: [makeWeightEntry("2024-05-23T08:00:00Z", 27600)],
      next_cursor: null,
      total_matching: 1,
    });
    const now = new Date("2024-05-23T12:00:00Z");
    const series = await fetchPetWeightSeries("pet-1", 30, now);

    expect(listJournalEntriesMock).toHaveBeenCalledWith("pet-1", {
      entryTypes: ["weight"],
      occurredFrom: new Date("2024-04-23T12:00:00Z").toISOString(),
      limit: 100,
    });
    expect(series).toEqual([{ date: "2024-05-23", label: "May 23", weightGrams: 27600 }]);
  });
});
