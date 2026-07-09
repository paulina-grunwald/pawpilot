import { describe, expect, it } from "vitest";
import {
  entryPresentation,
  formatKg,
  gramsToKg,
  groupEntriesByDay,
  kgToGrams,
} from "./journal.format";
import type { JournalEntryRead } from "./journal.schemas";

function makeEntry(overrides: Partial<JournalEntryRead> = {}): JournalEntryRead {
  return {
    id: "entry-1",
    pet_id: "pet-1",
    entry_type: "meal",
    payload: {
      entry_type: "meal",
      food_name: "Acana Grain-Free",
      brand: "Acana",
      amount_grams: 100,
      category: "kibble",
    },
    occurred_at: "2026-06-11T08:10:00Z",
    note: null,
    tags: [],
    is_concern: false,
    photo_path: null,
    photo_url: null,
    created_at: "2026-06-11T08:10:05Z",
    updated_at: "2026-06-11T08:10:05Z",
    ...overrides,
  };
}

describe("weight conversion", () => {
  it("formats grams as one-decimal kg", () => {
    expect(formatKg(21400)).toBe("21.4 kg");
    expect(formatKg(5000)).toBe("5.0 kg");
  });

  it("round-trips kg and grams", () => {
    expect(kgToGrams(21.4)).toBe(21400);
    expect(gramsToKg(21400)).toBe(21.4);
    expect(gramsToKg(kgToGrams(0.1))).toBe(0.1);
  });
});

describe("entryPresentation", () => {
  it("presents a meal with amount", () => {
    const presentation = entryPresentation(makeEntry());
    expect(presentation.title).toBe("Acana Grain-Free");
    expect(presentation.meta).toBe("Kibble · Acana");
    expect(presentation.value).toBe("100 g");
  });

  it("presents pee-only bathroom without stool details", () => {
    const presentation = entryPresentation(
      makeEntry({
        entry_type: "bathroom",
        payload: { entry_type: "bathroom", kind: "pee", bristol_score: null, color: null },
      }),
    );
    expect(presentation.title).toBe("Pee only");
  });

  it("presents a concerning poop with bristol type", () => {
    const presentation = entryPresentation(
      makeEntry({
        entry_type: "bathroom",
        is_concern: true,
        payload: { entry_type: "bathroom", kind: "poop", bristol_score: 6, color: "brown" },
      }),
    );
    expect(presentation.title).toBe("Poop · type 6 · brown");
    expect(presentation.meta).toBe("Worth watching");
  });

  it("presents a symptom from its tags and severity", () => {
    const presentation = entryPresentation(
      makeEntry({
        entry_type: "symptom",
        tags: ["scratch", "head-shake"],
        payload: { entry_type: "symptom", severity: 3, body_area: "ears" },
      }),
    );
    expect(presentation.title).toBe("scratch, head-shake");
    expect(presentation.meta).toBe("3/5 · moderate · area: ears");
  });

  it("presents mood, medication, weight, vet visit and note", () => {
    expect(
      entryPresentation(
        makeEntry({ entry_type: "mood", payload: { entry_type: "mood", score: 5 } }),
      ).title,
    ).toBe("playful · 5/5");

    expect(
      entryPresentation(
        makeEntry({
          entry_type: "medication",
          payload: {
            entry_type: "medication",
            drug_name: "Apoquel",
            dose: "16 mg",
            missed_dose: true,
          },
        }),
      ),
    ).toMatchObject({ title: "Apoquel · 16 mg", meta: "Missed dose" });

    expect(
      entryPresentation(
        makeEntry({
          entry_type: "weight",
          payload: { entry_type: "weight", weight_grams: 21400, source: "home_scale" },
        }),
      ),
    ).toMatchObject({ title: "Weight check", value: "21.4 kg" });

    expect(
      entryPresentation(
        makeEntry({
          entry_type: "vet_visit",
          payload: {
            entry_type: "vet_visit",
            reason: "Annual exam",
            diagnosis: "Healthy",
            follow_up: null,
            vet_name: "Dr. Patel",
          },
        }),
      ).title,
    ).toBe("Annual exam · Dr. Patel");

    expect(
      entryPresentation(
        makeEntry({
          entry_type: "free_note",
          payload: { entry_type: "free_note", text: "Big win at the park" },
        }),
      ).title,
    ).toBe("Big win at the park");
  });
});

describe("groupEntriesByDay", () => {
  const now = new Date("2026-06-11T14:00:00");

  it("groups consecutive same-day entries and labels today/yesterday", () => {
    const entries = [
      makeEntry({ id: "a", occurred_at: "2026-06-11T12:00:00" }),
      makeEntry({ id: "b", occurred_at: "2026-06-11T08:00:00" }),
      makeEntry({ id: "c", occurred_at: "2026-06-10T20:00:00" }),
      makeEntry({ id: "d", occurred_at: "2026-06-08T10:00:00" }),
    ];

    const groups = groupEntriesByDay(entries, now);

    expect(groups).toHaveLength(3);
    expect(groups[0].label).toBe("Today");
    expect(groups[0].isToday).toBe(true);
    expect(groups[0].entries.map((entry) => entry.id)).toEqual(["a", "b"]);
    expect(groups[1].label).toMatch(/^Yesterday/);
    expect(groups[2].isToday).toBe(false);
  });

  it("returns an empty list for no entries", () => {
    expect(groupEntriesByDay([], now)).toEqual([]);
  });
});
