import { describe, expect, it } from "vitest";
import type { PetRead } from "./pets";
import {
  formatAge,
  formatBirthday,
  formatBreed,
  formatLifeStage,
  formatSex,
  formatSexCompact,
  formatSpayedNeutered,
  formatWeightKg,
  toDashboardPet,
  toDetailPet,
} from "./pets.format";

function makePet(overrides: Partial<PetRead> = {}): PetRead {
  return {
    id: "pet-1",
    name: "Luna",
    breed_other: "Aussie mix",
    birthday: "2021-06-14",
    sex: "female",
    spayed_neutered: true,
    weight_grams: 22000,
    notes: null,
    photo_path: null,
    photo_url: null,
    created_at: "2026-05-23T00:00:00Z",
    updated_at: "2026-05-23T00:00:00Z",
    age_years: 4,
    age_months: 11,
    age_weeks: 256,
    life_stage: "adult",
    ...overrides,
  };
}

describe("formatAge", () => {
  it("shows weeks when under 9 weeks and under 1 year", () => {
    const pet = makePet({ age_years: 0, age_months: 1, age_weeks: 6 });
    expect(formatAge(pet)).toBe("6 weeks");
  });

  it("shows months when between 9 weeks and 1 year", () => {
    const pet = makePet({ age_years: 0, age_months: 4, age_weeks: 18 });
    expect(formatAge(pet)).toBe("4 months");
  });

  it("shows yrs + mo when between 1 and 3 years and singular yr", () => {
    const pet = makePet({ age_years: 1, age_months: 3 });
    expect(formatAge(pet)).toBe("1 yr 3 mo");
  });

  it("uses plural yrs between 2 and 3 years", () => {
    const pet = makePet({ age_years: 2, age_months: 4 });
    expect(formatAge(pet)).toBe("2 yrs 4 mo");
  });

  it("shows years only when 3+", () => {
    const pet = makePet({ age_years: 8, age_months: 2 });
    expect(formatAge(pet)).toBe("8 yrs");
  });
});

describe("formatWeightKg", () => {
  it("converts grams to kg with one decimal", () => {
    expect(formatWeightKg(22000)).toBe("22.0 kg");
    expect(formatWeightKg(550)).toBe("0.6 kg");
  });
});

describe("formatSex", () => {
  it("returns capitalized variant", () => {
    expect(formatSex("female")).toBe("Female");
    expect(formatSex("male")).toBe("Male");
  });
});

describe("formatSpayedNeutered", () => {
  it("returns Intact when not spayed", () => {
    expect(formatSpayedNeutered("female", false)).toBe("Intact");
    expect(formatSpayedNeutered("male", false)).toBe("Intact");
  });

  it("returns Spayed for female and Neutered for male", () => {
    expect(formatSpayedNeutered("female", true)).toBe("Spayed");
    expect(formatSpayedNeutered("male", true)).toBe("Neutered");
  });
});

describe("formatSexCompact", () => {
  it("combines status and sex in lowercase", () => {
    expect(formatSexCompact("female", true)).toBe("spayed female");
    expect(formatSexCompact("male", true)).toBe("neutered male");
    expect(formatSexCompact("female", false)).toBe("intact female");
    expect(formatSexCompact("male", false)).toBe("intact male");
  });
});

describe("formatBreed", () => {
  it("returns the breed name when present", () => {
    expect(formatBreed("Border Collie")).toBe("Border Collie");
  });

  it("falls back to Mixed / unknown when null", () => {
    expect(formatBreed(null)).toBe("Mixed / unknown");
  });
});

describe("formatLifeStage", () => {
  it("maps each stage to its title case label", () => {
    expect(formatLifeStage("puppy")).toBe("Puppy");
    expect(formatLifeStage("adolescent")).toBe("Adolescent");
    expect(formatLifeStage("adult")).toBe("Adult");
    expect(formatLifeStage("senior")).toBe("Senior");
  });
});

describe("formatBirthday", () => {
  it("renders an ISO date as a human-friendly string", () => {
    expect(formatBirthday("2021-06-14")).toMatch(/jun 14, 2021/i);
  });
});

describe("toDashboardPet", () => {
  it("returns a derived view including id and photoUrl", () => {
    const dashboard = toDashboardPet(makePet({ photo_url: "https://media/luna.jpg" }));
    expect(dashboard.id).toBe("pet-1");
    expect(dashboard.name).toBe("Luna");
    expect(dashboard.breed).toBe("Aussie mix");
    expect(dashboard.weightDisplay).toBe("22.0 kg");
    expect(dashboard.lifeStage).toBe("Adult");
    expect(dashboard.photoUrl).toBe("https://media/luna.jpg");
  });
});

describe("toDetailPet", () => {
  it("includes both sex and spayed/neutered display", () => {
    const detail = toDetailPet(
      makePet({ notes: "Loves frisbee.", sex: "male", spayed_neutered: false }),
    );
    expect(detail.sexDisplay).toBe("Male");
    expect(detail.spayedNeuteredDisplay).toBe("Intact");
    expect(detail.notes).toBe("Loves frisbee.");
    expect(detail.birthdayDisplay).toMatch(/jun 14, 2021/i);
  });

  it("returns an empty notes string when notes are null", () => {
    expect(toDetailPet(makePet({ notes: null })).notes).toBe("");
  });
});
