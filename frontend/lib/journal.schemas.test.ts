import { describe, expect, it } from "vitest";
import {
  journalEntryCreateSchema,
  journalEntryListResponseSchema,
  journalEntryReadSchema,
  journalPayloadSchema,
} from "./journal.schemas";

const BACKEND_PAYLOAD_FIXTURES = {
  meal: {
    entry_type: "meal",
    food_name: "Acana Grain-Free",
    brand: "Acana",
    amount_grams: 100,
    category: "kibble",
  },
  bathroom: { entry_type: "bathroom", kind: "poop", bristol_score: 4, color: "brown" },
  symptom: { entry_type: "symptom", severity: 3, body_area: "ears" },
  mood: { entry_type: "mood", score: 5 },
  medication: {
    entry_type: "medication",
    drug_name: "Apoquel",
    dose: "16 mg",
    missed_dose: false,
  },
  weight: { entry_type: "weight", weight_grams: 21400, source: "home_scale" },
  vet_visit: {
    entry_type: "vet_visit",
    reason: "Annual exam",
    diagnosis: "Healthy",
    follow_up: "In 2 weeks",
    vet_name: "Dr. Patel",
  },
  free_note: { entry_type: "free_note", text: "Met a friendly poodle at the park." },
} as const;

describe("journalPayloadSchema parity with backend fixtures", () => {
  for (const [entryType, fixture] of Object.entries(BACKEND_PAYLOAD_FIXTURES)) {
    it(`parses the ${entryType} fixture`, () => {
      const parsed = journalPayloadSchema.parse(fixture);
      expect(parsed.entry_type).toBe(entryType);
    });
  }

  it("rejects an unknown entry_type", () => {
    expect(() => journalPayloadSchema.parse({ entry_type: "walk", distance_km: 3 })).toThrow();
  });

  it("rejects bristol score with pee", () => {
    expect(() =>
      journalPayloadSchema.parse({
        entry_type: "bathroom",
        kind: "pee",
        bristol_score: 4,
        color: null,
      }),
    ).toThrow();
  });

  it("rejects out-of-range values mirroring backend rules", () => {
    expect(() => journalPayloadSchema.parse({ entry_type: "mood", score: 6 })).toThrow();
    expect(() =>
      journalPayloadSchema.parse({ entry_type: "symptom", severity: 0, body_area: null }),
    ).toThrow();
    expect(() =>
      journalPayloadSchema.parse({ entry_type: "weight", weight_grams: 99, source: "vet" }),
    ).toThrow();
  });
});

describe("journalEntryCreateSchema", () => {
  it("requires at least one tag on a symptom entry", () => {
    const result = journalEntryCreateSchema.safeParse({
      payload: BACKEND_PAYLOAD_FIXTURES.symptom,
      tags: [],
    });
    expect(result.success).toBe(false);
  });

  it("accepts a symptom entry with tags", () => {
    const result = journalEntryCreateSchema.safeParse({
      payload: BACKEND_PAYLOAD_FIXTURES.symptom,
      tags: ["scratch"],
    });
    expect(result.success).toBe(true);
  });

  it("defaults tags to an empty list for non-symptom entries", () => {
    const parsed = journalEntryCreateSchema.parse({ payload: BACKEND_PAYLOAD_FIXTURES.meal });
    expect(parsed.tags).toEqual([]);
  });

  it("caps tags at 20", () => {
    const result = journalEntryCreateSchema.safeParse({
      payload: BACKEND_PAYLOAD_FIXTURES.meal,
      tags: Array.from({ length: 21 }, (_, index) => `tag-${index}`),
    });
    expect(result.success).toBe(false);
  });
});

describe("journalEntryReadSchema", () => {
  const readFixture = {
    id: "entry-1",
    pet_id: "pet-1",
    entry_type: "symptom",
    payload: BACKEND_PAYLOAD_FIXTURES.symptom,
    occurred_at: "2026-06-11T08:10:00Z",
    note: "Shaking her head",
    tags: ["scratch", "head-shake"],
    is_concern: true,
    photo_path: null,
    photo_url: null,
    created_at: "2026-06-11T08:10:05Z",
    updated_at: "2026-06-11T08:10:05Z",
  };

  it("parses a full read fixture", () => {
    const parsed = journalEntryReadSchema.parse(readFixture);
    expect(parsed.is_concern).toBe(true);
    expect(parsed.payload.entry_type).toBe("symptom");
  });

  it("parses the list envelope", () => {
    const parsed = journalEntryListResponseSchema.parse({
      items: [readFixture],
      next_cursor: null,
      total_matching: 1,
    });
    expect(parsed.items).toHaveLength(1);
    expect(parsed.total_matching).toBe(1);
  });
});
