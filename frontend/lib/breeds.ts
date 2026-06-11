import { getApiBaseUrl } from "./auth";

export type BreedRead = {
  name: string;
  group: string | null;
  size_category: "toy" | "small" | "medium" | "large" | "giant" | null;
};

export async function searchBreeds(query: string, limit = 20): Promise<BreedRead[]> {
  const url = new URL(`${getApiBaseUrl()}/breeds`);
  if (query) url.searchParams.set("q", query);
  url.searchParams.set("limit", String(limit));
  const response = await fetch(url.toString(), { credentials: "include", cache: "no-store" });
  if (!response.ok) {
    throw new Error(`GET /breeds failed with ${response.status}`);
  }
  return (await response.json()) as BreedRead[];
}
