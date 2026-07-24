import { describe, expect, it } from "vitest";
import { computeJournalStats, relativeTime } from "./journal.stats";
import type { JournalEntryRead, JournalPayload } from "./journal.schemas";

const NOW = new Date("2026-07-09T21:00:00Z");

function makeEntry(
  payload: JournalPayload,
  overrides: Partial<JournalEntryRead> = {},
): JournalEntryRead {
  return {
    id: "entry-1",
    pet_id: "pet-1",
    entry_type: payload.entry_type,
    payload,
    occurred_at: NOW.toISOString(),
    note: null,
    tags: [],
    is_concern: false,
    photo_path: null,
    photo_url: null,
    created_at: NOW.toISOString(),
    updated_at: NOW.toISOString(),
    ...overrides,
  };
}

function statsByKey(entries: JournalEntryRead[], now: Date | null = NOW) {
  return Object.fromEntries(computeJournalStats(entries, now).map((stat) => [stat.key, stat]));
}

describe("relativeTime", () => {
  it.each([
    [20 * 1000, "just now"],
    [5 * 60 * 1000, "5m ago"],
    [3 * 60 * 60 * 1000, "3h ago"],
    [2 * 24 * 60 * 60 * 1000, "2d ago"],
    [3 * 7 * 24 * 60 * 60 * 1000, "3w ago"],
  ])("formats %ims elapsed as %s", (elapsedMs, expected) => {
    const occurredAt = new Date(NOW.getTime() - elapsedMs).toISOString();
    expect(relativeTime(occurredAt, NOW)).toBe(expected);
  });
});

describe("computeJournalStats", () => {
  it("returns four stats in a fixed order", () => {
    const stats = computeJournalStats([], NOW);
    expect(stats.map((stat) => stat.key)).toEqual(["weight", "meal", "medication", "attention"]);
  });

  it("marks every stat absent for an empty journal", () => {
    const stats = statsByKey([]);
    expect(stats.weight.present).toBe(false);
    expect(stats.weight.value).toBe("—");
    expect(stats.meal.subtitle).toBe("No meals logged");
    expect(stats.medication.subtitle).toBe("No active meds");
    expect(stats.attention.subtitle).toBe("All clear");
    expect(stats.attention.value).toBe("0");
  });

  it("summarizes the newest weight with a downward delta and chronological sparkline", () => {
    const entries = [
      makeEntry({ entry_type: "weight", weight_grams: 28000, source: "vet" }),
      makeEntry({ entry_type: "weight", weight_grams: 28600, source: "home_scale" }),
    ];
    const { weight } = statsByKey(entries);
    expect(weight.value).toBe("28.0");
    expect(weight.unit).toBe("kg");
    expect(weight.subtitle).toBe("↓ 0.6 kg recently");
    expect(weight.sparkline).toEqual([28600, 28000]);
    expect(weight.present).toBe(true);
  });

  it("reports a first reading when only one weight exists", () => {
    const { weight } = statsByKey([
      makeEntry({ entry_type: "weight", weight_grams: 28000, source: "vet" }),
    ]);
    expect(weight.subtitle).toBe("First reading logged");
  });

  it("reports steady weight when the delta rounds to zero", () => {
    const { weight } = statsByKey([
      makeEntry({ entry_type: "weight", weight_grams: 28020, source: "vet" }),
      makeEntry({ entry_type: "weight", weight_grams: 28000, source: "vet" }),
    ]);
    expect(weight.subtitle).toBe("Steady over recent logs");
  });

  it("summarizes the last meal amount and food", () => {
    const { meal } = statsByKey([
      makeEntry(
        {
          entry_type: "meal",
          food_name: "Chicken",
          brand: null,
          amount_grams: 200,
          category: "kibble",
        },
        { occurred_at: new Date(NOW.getTime() - 3 * 60 * 60 * 1000).toISOString() },
      ),
    ]);
    expect(meal.value).toBe("200");
    expect(meal.unit).toBe("g");
    expect(meal.subtitle).toBe("Chicken · 3h ago");
  });

  it("falls back to the food name when a meal has no amount", () => {
    const { meal } = statsByKey([
      makeEntry({
        entry_type: "meal",
        food_name: "Treats",
        brand: null,
        amount_grams: null,
        category: "treat",
      }),
    ]);
    expect(meal.value).toBe("Treats");
    expect(meal.unit).toBe("");
  });

  it("falls back to an absolute date when now is not yet available (pre-hydration)", () => {
    const { meal } = statsByKey(
      [
        makeEntry(
          {
            entry_type: "meal",
            food_name: "Chicken",
            brand: null,
            amount_grams: 200,
            category: "kibble",
          },
          { occurred_at: "2026-07-07T08:00:00Z" },
        ),
      ],
      null,
    );
    expect(meal.subtitle).toBe("Chicken · Jul 7");
  });

  it("summarizes the active medication and flags a missed dose", () => {
    const { medication } = statsByKey([
      makeEntry({
        entry_type: "medication",
        drug_name: "Apoquel",
        dose: "16 mg",
        missed_dose: true,
      }),
    ]);
    expect(medication.value).toBe("Apoquel");
    expect(medication.label).toBe("Active med");
    expect(medication.subtitle).toMatch(/^Missed · /);
  });

  it("keeps the Active med label for a recent, non-missed dose", () => {
    const { medication } = statsByKey([
      makeEntry(
        { entry_type: "medication", drug_name: "Apoquel", dose: "16 mg", missed_dose: false },
        { occurred_at: new Date(NOW.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString() },
      ),
    ]);
    expect(medication.label).toBe("Active med");
  });

  it("relabels a stale, non-missed medication as Last medication instead of claiming it's active", () => {
    const { medication } = statsByKey([
      makeEntry(
        { entry_type: "medication", drug_name: "Amoxicillin", dose: "250 mg", missed_dose: false },
        { occurred_at: new Date(NOW.getTime() - 42 * 24 * 60 * 60 * 1000).toISOString() },
      ),
    ]);
    expect(medication.label).toBe("Last medication");
    expect(medication.value).toBe("Amoxicillin");
  });

  it("keeps the Missed label priority even when a missed dose is stale", () => {
    const { medication } = statsByKey([
      makeEntry(
        { entry_type: "medication", drug_name: "Amoxicillin", dose: "250 mg", missed_dose: true },
        { occurred_at: new Date(NOW.getTime() - 42 * 24 * 60 * 60 * 1000).toISOString() },
      ),
    ]);
    expect(medication.label).toBe("Active med");
    expect(medication.subtitle).toMatch(/^Missed · /);
  });

  it("does not flag a medication as stale before now is available (pre-hydration)", () => {
    const { medication } = statsByKey(
      [
        makeEntry(
          {
            entry_type: "medication",
            drug_name: "Amoxicillin",
            dose: "250 mg",
            missed_dose: false,
          },
          { occurred_at: new Date(NOW.getTime() - 42 * 24 * 60 * 60 * 1000).toISOString() },
        ),
      ],
      null,
    );
    expect(medication.label).toBe("Active med");
  });

  it("counts concern entries and describes the most recent one", () => {
    const { attention } = statsByKey([
      makeEntry(
        { entry_type: "symptom", severity: 3, body_area: "paws" },
        { is_concern: true, tags: ["itchy"], occurred_at: "2026-07-07T08:00:00Z" },
      ),
      makeEntry({
        entry_type: "meal",
        food_name: "Chicken",
        brand: null,
        amount_grams: 200,
        category: "kibble",
      }),
    ]);
    expect(attention.value).toBe("1");
    expect(attention.unit).toBe("flag");
    expect(attention.subtitle).toBe("itchy · Jul 7");
    expect(attention.present).toBe(true);
    expect(attention.iconType).toBe("symptom");
  });

  it("uses the most recent concern's own entry type for the icon and accent, not always symptom", () => {
    const { attention } = statsByKey([
      makeEntry(
        { entry_type: "medication", drug_name: "Apoquel", dose: "16 mg", missed_dose: true },
        { is_concern: true, occurred_at: "2026-07-08T08:00:00Z" },
      ),
      makeEntry(
        { entry_type: "symptom", severity: 2, body_area: "ears" },
        { is_concern: true, tags: ["itchy"], occurred_at: "2026-07-01T08:00:00Z" },
      ),
    ]);
    expect(attention.iconType).toBe("medication");
    expect(attention.accentVar).toBe("--blue-deep");
    expect(attention.value).toBe("2");
  });
});
