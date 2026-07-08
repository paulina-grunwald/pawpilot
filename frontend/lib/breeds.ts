import { getApiBaseUrl } from "./auth";

export type BreedRead = {
  name: string;
  group: string | null;
  size_category: "toy" | "small" | "medium" | "large" | "giant" | null;
};

export async function searchBreeds(query: string, limit = 20): Promise<BreedRead[]> {
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  params.set("limit", String(limit));
  const response = await fetch(`${getApiBaseUrl()}/breeds?${params.toString()}`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`GET /breeds failed with ${response.status}`);
  }
  return (await response.json()) as BreedRead[];
}
