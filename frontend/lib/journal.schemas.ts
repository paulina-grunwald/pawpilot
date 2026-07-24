import { z } from "zod";
import {
  BATHROOM_COLORS,
  BATHROOM_KINDS,
  BODY_AREAS,
  MAX_NOTE_LENGTH,
  MAX_TAG_LENGTH,
  MAX_TAGS,
  MEAL_CATEGORIES,
  WEIGHT_SOURCES,
} from "./journal.constants";

export const mealPayloadSchema = z.object({
  entry_type: z.literal("meal"),
  food_name: z.string().trim().min(1, "Food name is required").max(200),
  brand: z.string().max(200).nullable(),
  amount_grams: z.number().int().positive("Amount must be positive").nullable(),
  category: z.enum(MEAL_CATEGORIES),
});

export const bathroomPayloadSchema = z
  .object({
    entry_type: z.literal("bathroom"),
    kind: z.enum(BATHROOM_KINDS),
    bristol_score: z.number().int().min(1).max(7).nullable(),
    color: z.enum(BATHROOM_COLORS).nullable(),
  })
  .refine(
    (value) => value.kind !== "pee" || (value.bristol_score === null && value.color === null),
    {
      message: "Stool details are only allowed when kind includes poop",
      path: ["bristol_score"],
    },
  );

export const symptomPayloadSchema = z.object({
  entry_type: z.literal("symptom"),
  severity: z.number().int().min(1).max(5),
  body_area: z.enum(BODY_AREAS).nullable(),
});

export const moodPayloadSchema = z.object({
  entry_type: z.literal("mood"),
  score: z.number().int().min(1).max(5),
});

export const medicationPayloadSchema = z.object({
  entry_type: z.literal("medication"),
  drug_name: z.string().trim().min(1, "Drug name is required").max(200),
  dose: z.string().trim().min(1, "Dose is required").max(200),
  missed_dose: z.boolean(),
});

export const weightPayloadSchema = z.object({
  entry_type: z.literal("weight"),
  weight_grams: z.number().int().min(100).max(120000),
  source: z.enum(WEIGHT_SOURCES),
});

export const vetVisitPayloadSchema = z.object({
  entry_type: z.literal("vet_visit"),
  reason: z.string().trim().min(1, "Reason is required").max(500),
  diagnosis: z.string().max(2000).nullable(),
  follow_up: z.string().max(500).nullable(),
  vet_name: z.string().max(200).nullable(),
});

export const freeNotePayloadSchema = z.object({
  entry_type: z.literal("free_note"),
  text: z.string().trim().min(1, "Write something first").max(2000),
});

export const journalPayloadSchema = z.discriminatedUnion("entry_type", [
  mealPayloadSchema,
  bathroomPayloadSchema,
  symptomPayloadSchema,
  moodPayloadSchema,
  medicationPayloadSchema,
  weightPayloadSchema,
  vetVisitPayloadSchema,
  freeNotePayloadSchema,
]);

export type JournalPayload = z.infer<typeof journalPayloadSchema>;
export type MealPayload = z.infer<typeof mealPayloadSchema>;
export type BathroomPayload = z.infer<typeof bathroomPayloadSchema>;
export type SymptomPayload = z.infer<typeof symptomPayloadSchema>;
export type MoodPayload = z.infer<typeof moodPayloadSchema>;
export type MedicationPayload = z.infer<typeof medicationPayloadSchema>;
export type WeightPayload = z.infer<typeof weightPayloadSchema>;
export type VetVisitPayload = z.infer<typeof vetVisitPayloadSchema>;
export type FreeNotePayload = z.infer<typeof freeNotePayloadSchema>;

export const journalTagsSchema = z
  .array(z.string().trim().min(1).max(MAX_TAG_LENGTH))
  .max(MAX_TAGS, `At most ${MAX_TAGS} tags`);

export const journalEntryCreateSchema = z
  .object({
    payload: journalPayloadSchema,
    occurred_at: z.string().nullable().optional(),
    note: z.string().max(MAX_NOTE_LENGTH).nullable().optional(),
    tags: journalTagsSchema.default([]),
  })
  .refine((value) => value.payload.entry_type !== "symptom" || value.tags.length > 0, {
    message: "Pick at least one symptom tag",
    path: ["tags"],
  });

export type JournalEntryCreateInput = z.infer<typeof journalEntryCreateSchema>;

export const journalEntryReadSchema = z.object({
  id: z.string(),
  pet_id: z.string(),
  entry_type: z.string(),
  payload: journalPayloadSchema,
  occurred_at: z.string(),
  note: z.string().nullable(),
  tags: z.array(z.string()),
  is_concern: z.boolean(),
  photo_path: z.string().nullable(),
  photo_url: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type JournalEntryRead = z.infer<typeof journalEntryReadSchema>;

export const journalEntryListResponseSchema = z.object({
  items: z.array(journalEntryReadSchema),
  next_cursor: z.string().nullable(),
  total_matching: z.number().int(),
});

export type JournalEntryListResponse = z.infer<typeof journalEntryListResponseSchema>;
