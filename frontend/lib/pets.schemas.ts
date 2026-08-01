import { z } from "zod";
import type { PetCreateInput, PetRead, PetUpdateInput } from "./pets";

const MAX_AGE_YEARS = 22;

function today(): Date {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

function parseLocalDate(isoDate: string): Date {
  const [year, month, day] = isoDate.split("-").map(Number);
  if ([year, month, day].some(Number.isNaN)) return new Date(Number.NaN);
  return new Date(year, month - 1, day);
}

function earliestAllowedBirthday(): Date {
  const reference = today();
  return new Date(
    reference.getFullYear() - MAX_AGE_YEARS,
    reference.getMonth(),
    reference.getDate(),
  );
}

export const petFormSchema = z.object({
  name: z
    .string({ error: "Name is required" })
    .trim()
    .min(1, "Name is required")
    .max(60, "Name must be 60 characters or fewer"),
  breedOther: z
    .string()
    .trim()
    .max(80, "Breed must be 80 characters or fewer")
    .optional()
    .or(z.literal("")),
  birthday: z
    .string({ error: "Birthday is required" })
    .min(1, "Birthday is required")
    .refine((value) => !Number.isNaN(Date.parse(value)), "Enter a valid date")
    .refine((value) => parseLocalDate(value) <= today(), "Birthday must be in the past")
    .refine(
      (value) => parseLocalDate(value) >= earliestAllowedBirthday(),
      `Birthday cannot be more than ${MAX_AGE_YEARS} years ago`,
    ),
  sex: z.enum(["male", "female"], { error: "Pick a sex" }),
  spayedNeutered: z.boolean(),
  weightKg: z
    .number({ error: "Weight is required" })
    .min(0.1, "Weight must be at least 0.1 kg")
    .max(120, "Weight must be 120 kg or less"),
  notes: z
    .string()
    .max(1000, "Notes must be 1000 characters or fewer")
    .optional()
    .or(z.literal("")),
});

export type PetFormInput = z.infer<typeof petFormSchema>;

function normaliseOptional(value: string | undefined): string | null {
  if (value === undefined) return null;
  const trimmed = value.trim();
  return trimmed.length === 0 ? null : trimmed;
}

export function toCreateInput(values: PetFormInput): PetCreateInput {
  return {
    name: values.name.trim(),
    breed_other: normaliseOptional(values.breedOther),
    birthday: values.birthday,
    sex: values.sex,
    spayed_neutered: values.spayedNeutered,
    weight_grams: Math.round(values.weightKg * 1000),
    notes: normaliseOptional(values.notes),
  };
}

export function toUpdateInput(values: PetFormInput): PetUpdateInput {
  return toCreateInput(values);
}

export function petReadToFormInput(pet: PetRead): PetFormInput {
  return {
    name: pet.name,
    breedOther: pet.breed_other ?? "",
    birthday: pet.birthday,
    sex: pet.sex,
    spayedNeutered: pet.spayed_neutered,
    weightKg: Math.round(pet.weight_grams) / 1000,
    notes: pet.notes ?? "",
  };
}
