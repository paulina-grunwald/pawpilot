import { describe, expect, it } from "vitest";
import type { PetRead } from "./pets";
import { petFormSchema, petReadToFormInput, toCreateInput, toUpdateInput } from "./pets.schemas";

function validInput() {
  return {
    name: "Luna",
    breedOther: "Aussie mix",
    birthday: "2021-06-14",
    sex: "female" as const,
    spayedNeutered: true,
    weightKg: 22,
    notes: "Loves frisbee.",
  };
}

function isoYearsAgo(years: number): string {
  const now = new Date();
  return new Date(now.getFullYear() - years, now.getMonth(), now.getDate())
    .toISOString()
    .slice(0, 10);
}

describe("petFormSchema", () => {
  it("accepts a fully valid input", () => {
    expect(petFormSchema.safeParse(validInput()).success).toBe(true);
  });

  it("rejects empty names", () => {
    const result = petFormSchema.safeParse({ ...validInput(), name: "" });
    expect(result.success).toBe(false);
  });

  it("rejects names longer than 60 chars", () => {
    const result = petFormSchema.safeParse({ ...validInput(), name: "x".repeat(61) });
    expect(result.success).toBe(false);
  });

  it("rejects future birthdays", () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const result = petFormSchema.safeParse({
      ...validInput(),
      birthday: tomorrow.toISOString().slice(0, 10),
    });
    expect(result.success).toBe(false);
  });

  it("rejects birthdays more than 22 years ago", () => {
    const result = petFormSchema.safeParse({ ...validInput(), birthday: isoYearsAgo(30) });
    expect(result.success).toBe(false);
  });

  it("rejects weight below 0.1 kg", () => {
    expect(petFormSchema.safeParse({ ...validInput(), weightKg: 0.05 }).success).toBe(false);
  });

  it("rejects weight above 120 kg", () => {
    expect(petFormSchema.safeParse({ ...validInput(), weightKg: 200 }).success).toBe(false);
  });

  it("rejects notes longer than 1000 chars", () => {
    expect(petFormSchema.safeParse({ ...validInput(), notes: "n".repeat(1001) }).success).toBe(
      false,
    );
  });

  it("accepts empty breed and notes", () => {
    expect(petFormSchema.safeParse({ ...validInput(), breedOther: "", notes: "" }).success).toBe(
      true,
    );
  });
});

describe("toCreateInput", () => {
  it("trims strings, converts kg to grams, and nulls empty optionals", () => {
    const created = toCreateInput({
      ...validInput(),
      name: "  Luna  ",
      breedOther: "",
      notes: "",
      weightKg: 22.5,
    });
    expect(created.name).toBe("Luna");
    expect(created.breed_other).toBeNull();
    expect(created.notes).toBeNull();
    expect(created.weight_grams).toBe(22500);
  });

  it("preserves non-empty breed and notes", () => {
    const created = toCreateInput(validInput());
    expect(created.breed_other).toBe("Aussie mix");
    expect(created.notes).toBe("Loves frisbee.");
  });
});

describe("toUpdateInput", () => {
  it("matches toCreateInput shape", () => {
    expect(toUpdateInput(validInput())).toEqual(toCreateInput(validInput()));
  });
});

describe("petReadToFormInput", () => {
  it("converts grams to kg and nulls to empty strings", () => {
    const pet: PetRead = {
      id: "pet-1",
      name: "Luna",
      breed_other: null,
      birthday: "2021-06-14",
      sex: "female",
      spayed_neutered: true,
      weight_grams: 22500,
      notes: null,
      photo_path: null,
      photo_url: null,
      created_at: "2026-05-23T00:00:00Z",
      updated_at: "2026-05-23T00:00:00Z",
      age_years: 4,
      age_months: 11,
      age_weeks: 256,
      life_stage: "adult",
    };
    const formInput = petReadToFormInput(pet);
    expect(formInput.breedOther).toBe("");
    expect(formInput.notes).toBe("");
    expect(formInput.weightKg).toBe(22.5);
  });
});
