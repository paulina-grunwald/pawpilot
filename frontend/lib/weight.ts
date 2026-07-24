import { formatMonthDay } from "./date";
import { listJournalEntries } from "./journal";
import type { JournalEntryRead } from "./journal.schemas";

export type WeightSeriesPoint = {
  date: string;
  label: string;
  weightGrams: number;
};

export function toWeightSeries(entries: readonly JournalEntryRead[]): WeightSeriesPoint[] {
  const latestByDay = new Map<string, { occurredAt: string; weightGrams: number }>();
  for (const entry of entries) {
    if (entry.payload.entry_type !== "weight") continue;
    const date = entry.occurred_at.slice(0, 10);
    const existing = latestByDay.get(date);
    if (!existing || entry.occurred_at > existing.occurredAt) {
      latestByDay.set(date, {
        occurredAt: entry.occurred_at,
        weightGrams: entry.payload.weight_grams,
      });
    }
  }

  return [...latestByDay.entries()]
    .sort(([firstDate], [secondDate]) => firstDate.localeCompare(secondDate))
    .map(([date, reading]) => ({
      date,
      label: formatMonthDay(date),
      weightGrams: reading.weightGrams,
    }));
}

export function meanWeightGrams(series: readonly WeightSeriesPoint[]): number | null {
  if (series.length === 0) return null;
  const total = series.reduce((sum, point) => sum + point.weightGrams, 0);
  return total / series.length;
}

export function formatWeightKg(weightGrams: number): string {
  return `${(weightGrams / 1000).toFixed(1)} kg`;
}

export async function fetchPetWeightSeries(
  petId: string,
  days: number,
  now: Date = new Date(),
): Promise<WeightSeriesPoint[]> {
  const from = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
  const response = await listJournalEntries(petId, {
    entryTypes: ["weight"],
    occurredFrom: from.toISOString(),
    limit: 100,
  });
  return toWeightSeries(response.items);
}
