import { getApiBaseUrl } from "./auth";

export type PetSex = "male" | "female";
export type PetLifeStage = "puppy" | "adolescent" | "adult" | "senior";

export type PetRead = {
  id: string;
  name: string;
  breed_other: string | null;
  birthday: string;
  sex: PetSex;
  spayed_neutered: boolean;
  weight_grams: number;
  notes: string | null;
  photo_path: string | null;
  photo_url: string | null;
  created_at: string;
  updated_at: string;
  age_years: number;
  age_months: number;
  age_weeks: number;
  life_stage: PetLifeStage;
};

export type PetCreateInput = {
  name: string;
  breed_other?: string | null;
  birthday: string;
  sex: PetSex;
  spayed_neutered: boolean;
  weight_grams: number;
  notes?: string | null;
};

export type PetUpdateInput = Partial<PetCreateInput>;

export type PetsErrorCode =
  | "PET_NOT_FOUND"
  | "PET_VALIDATION_ERROR"
  | "PET_UNAUTHENTICATED"
  | "PET_PHOTO_UNSUPPORTED_MEDIA_TYPE"
  | "PET_PHOTO_TOO_LARGE"
  | "NETWORK_ERROR"
  | "UNKNOWN";

export class PetsError extends Error {
  readonly code: PetsErrorCode;
  readonly status?: number;

  constructor(code: PetsErrorCode, message: string, status?: number) {
    super(message);
    this.code = code;
    this.status = status;
    this.name = "PetsError";
  }
}

function petsErrorForStatus(status: number): PetsErrorCode {
  if (status === 401) return "PET_UNAUTHENTICATED";
  if (status === 404) return "PET_NOT_FOUND";
  if (status === 413) return "PET_PHOTO_TOO_LARGE";
  if (status === 415) return "PET_PHOTO_UNSUPPORTED_MEDIA_TYPE";
  if (status === 422) return "PET_VALIDATION_ERROR";
  return "UNKNOWN";
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new PetsError(
      petsErrorForStatus(response.status),
      `Request failed with ${response.status}`,
      response.status,
    );
  }
  return (await response.json()) as T;
}

export async function listPetsForBrowser(): Promise<PetRead[]> {
  const response = await fetch(`${getApiBaseUrl()}/pets`, {
    credentials: "include",
    cache: "no-store",
  });
  return readJson<PetRead[]>(response);
}

export async function createPet(payload: PetCreateInput): Promise<PetRead> {
  const response = await fetch(`${getApiBaseUrl()}/pets`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return readJson<PetRead>(response);
}

export async function updatePet(petId: string, payload: PetUpdateInput): Promise<PetRead> {
  const response = await fetch(`${getApiBaseUrl()}/pets/${petId}`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return readJson<PetRead>(response);
}

export async function deletePet(petId: string): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/pets/${petId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) {
    throw new PetsError(
      petsErrorForStatus(response.status),
      `DELETE /pets/${petId} failed with ${response.status}`,
      response.status,
    );
  }
}

export async function uploadPetPhoto(petId: string, file: File): Promise<PetRead> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${getApiBaseUrl()}/pets/${petId}/photo`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  return readJson<PetRead>(response);
}

export async function deletePetPhoto(petId: string): Promise<PetRead> {
  const response = await fetch(`${getApiBaseUrl()}/pets/${petId}/photo`, {
    method: "DELETE",
    credentials: "include",
  });
  return readJson<PetRead>(response);
}
