import "server-only";
import { cookies } from "next/headers";
import { AUTH_COOKIE_NAME } from "./auth.constants";
import { getApiBaseUrl } from "./auth";
import { PetsError, type PetRead } from "./pets";

async function getCookieHeader(): Promise<string | null> {
  const cookieStore = await cookies();
  const authCookie = cookieStore.get(AUTH_COOKIE_NAME);
  if (!authCookie) return null;
  return `${authCookie.name}=${authCookie.value}`;
}

export async function fetchPetsForCurrentUser(): Promise<PetRead[]> {
  const cookieHeader = await getCookieHeader();
  if (!cookieHeader) {
    throw new PetsError("PET_UNAUTHENTICATED", "no auth cookie", 401);
  }
  const response = await fetch(`${getApiBaseUrl()}/pets`, {
    headers: { cookie: cookieHeader },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new PetsError(
      response.status === 401 ? "PET_UNAUTHENTICATED" : "UNKNOWN",
      `GET /pets failed with ${response.status}`,
      response.status,
    );
  }
  return (await response.json()) as PetRead[];
}

export async function fetchPetById(petId: string): Promise<PetRead | null> {
  const cookieHeader = await getCookieHeader();
  if (!cookieHeader) {
    throw new PetsError("PET_UNAUTHENTICATED", "no auth cookie", 401);
  }
  const response = await fetch(`${getApiBaseUrl()}/pets/${petId}`, {
    headers: { cookie: cookieHeader },
    cache: "no-store",
  });
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new PetsError(
      response.status === 401 ? "PET_UNAUTHENTICATED" : "UNKNOWN",
      `GET /pets/${petId} failed with ${response.status}`,
      response.status,
    );
  }
  return (await response.json()) as PetRead;
}
