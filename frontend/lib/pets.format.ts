import type { PetRead, PetSex, PetLifeStage } from "./pets";

const LIFE_STAGE_LABELS: Record<PetLifeStage, string> = {
  puppy: "Puppy",
  adolescent: "Adolescent",
  adult: "Adult",
  senior: "Senior",
};

export function formatAge(pet: PetRead): string {
  if (pet.age_years < 1) {
    if (pet.age_weeks < 9) return `${pet.age_weeks} weeks`;
    return `${pet.age_months} months`;
  }
  if (pet.age_years < 3) {
    return `${pet.age_years} ${pet.age_years === 1 ? "yr" : "yrs"} ${pet.age_months} mo`;
  }
  return `${pet.age_years} yrs`;
}

export function formatWeightKg(grams: number): string {
  return `${(grams / 1000).toFixed(1)} kg`;
}

export function formatSex(sex: PetSex): string {
  return sex === "female" ? "Female" : "Male";
}

export function formatSpayedNeutered(sex: PetSex, spayed: boolean): string {
  if (!spayed) return "Intact";
  return sex === "female" ? "Spayed" : "Neutered";
}

export function formatSexCompact(sex: PetSex, spayed: boolean): string {
  const status = spayed ? formatSpayedNeutered(sex, spayed).toLowerCase() : "intact";
  return `${status} ${sex === "female" ? "female" : "male"}`;
}

export function formatBreed(breedOther: string | null): string {
  return breedOther ?? "Mixed / unknown";
}

export function formatLifeStage(stage: PetLifeStage): string {
  return LIFE_STAGE_LABELS[stage];
}

export function formatBirthday(isoDate: string): string {
  const parsed = new Date(`${isoDate}T00:00:00`);
  return parsed.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export type DashboardPetView = {
  name: string;
  breed: string;
  ageDisplay: string;
  weightDisplay: string;
  sexDisplay: string;
  lifeStage: string;
  photoUrl?: string | null;
};

export type PetDetailView = {
  id: string;
  name: string;
  breed: string;
  sexDisplay: string;
  spayedNeuteredDisplay: string;
  lifeStage: string;
  ageDisplay: string;
  birthdayDisplay: string;
  weightDisplay: string;
  notes: string;
  photoUrl?: string | null;
};

export function toDashboardPet(pet: PetRead): DashboardPetView {
  return {
    name: pet.name,
    breed: formatBreed(pet.breed_other),
    ageDisplay: formatAge(pet),
    weightDisplay: formatWeightKg(pet.weight_grams),
    sexDisplay: formatSexCompact(pet.sex, pet.spayed_neutered),
    lifeStage: formatLifeStage(pet.life_stage),
    photoUrl: pet.photo_url,
  };
}

export function toDetailPet(pet: PetRead): PetDetailView {
  return {
    id: pet.id,
    name: pet.name,
    breed: formatBreed(pet.breed_other),
    sexDisplay: formatSex(pet.sex),
    spayedNeuteredDisplay: formatSpayedNeutered(pet.sex, pet.spayed_neutered),
    lifeStage: formatLifeStage(pet.life_stage),
    ageDisplay: formatAge(pet),
    birthdayDisplay: formatBirthday(pet.birthday),
    weightDisplay: formatWeightKg(pet.weight_grams),
    notes: pet.notes ?? "",
    photoUrl: pet.photo_url,
  };
}
