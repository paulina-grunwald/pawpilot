import { ENTRY_TYPE_META, type EntryType } from "./journal.constants";
import { entryPresentation } from "./journal.format";
import type { JournalEntryRead } from "./journal.schemas";

export type StatKey = "weight" | "meal" | "medication" | "attention";

export type JournalStat = {
  key: StatKey;
  label: string;
  accentVar: string;
  iconType: EntryType;
  value: string;
  unit: string;
  sub: string;
  sparkline: number[] | null;
  present: boolean;
};

const PLACEHOLDER = "—";

export function relativeTime(occurredAt: string, now: Date = new Date()): string {
  const elapsedMs = now.getTime() - new Date(occurredAt).getTime();
  const minutes = Math.round(elapsedMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  const weeks = Math.round(days / 7);
  return `${weeks}w ago`;
}

function shortDate(occurredAt: string): string {
  return new Date(occurredAt).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function weightKg(weightGrams: number): string {
  return (weightGrams / 1000).toFixed(1);
}

function weightStat(entries: JournalEntryRead[]): JournalStat {
  const meta = ENTRY_TYPE_META.weight;
  const base = { key: "weight" as const, label: "Current weight", accentVar: meta.accentVar, iconType: "weight" as EntryType };
  const weights = entries.filter(
    (entry): entry is JournalEntryRead & { payload: { entry_type: "weight"; weight_grams: number } } =>
      entry.payload.entry_type === "weight",
  );
  if (weights.length === 0) {
    return { ...base, value: PLACEHOLDER, unit: "kg", sub: "No weigh-ins yet", sparkline: null, present: false };
  }
  // entries are newest-first; oldest is last, chronological runs oldest -> newest.
  const newest = weights[0].payload.weight_grams;
  const oldest = weights[weights.length - 1].payload.weight_grams;
  const sparkline = weights.map((entry) => entry.payload.weight_grams).reverse();
  let sub = "First reading logged";
  if (weights.length > 1) {
    const deltaKg = (newest - oldest) / 1000;
    const magnitude = Math.abs(deltaKg).toFixed(1);
    if (magnitude === "0.0") {
      sub = "Steady over recent logs";
    } else {
      sub = `${deltaKg < 0 ? "↓" : "↑"} ${magnitude} kg recently`;
    }
  }
  return { ...base, value: weightKg(newest), unit: "kg", sub, sparkline, present: true };
}

function mealStat(entries: JournalEntryRead[], now: Date): JournalStat {
  const meta = ENTRY_TYPE_META.meal;
  const base = { key: "meal" as const, label: "Last meal", accentVar: meta.accentVar, iconType: "meal" as EntryType };
  const meal = entries.find((entry) => entry.payload.entry_type === "meal");
  if (!meal || meal.payload.entry_type !== "meal") {
    return { ...base, value: PLACEHOLDER, unit: "", sub: "No meals logged", sparkline: null, present: false };
  }
  const grams = meal.payload.amount_grams;
  return {
    ...base,
    value: grams !== null ? String(grams) : meal.payload.food_name,
    unit: grams !== null ? "g" : "",
    sub: `${meal.payload.food_name} · ${relativeTime(meal.occurred_at, now)}`,
    sparkline: null,
    present: true,
  };
}

function medicationStat(entries: JournalEntryRead[], now: Date): JournalStat {
  const meta = ENTRY_TYPE_META.medication;
  const base = {
    key: "medication" as const,
    label: "Active med",
    accentVar: meta.accentVar,
    iconType: "medication" as EntryType,
  };
  const medication = entries.find((entry) => entry.payload.entry_type === "medication");
  if (!medication || medication.payload.entry_type !== "medication") {
    return { ...base, value: PLACEHOLDER, unit: "", sub: "No active meds", sparkline: null, present: false };
  }
  const sub = medication.payload.missed_dose
    ? `Missed · ${relativeTime(medication.occurred_at, now)}`
    : `${medication.payload.dose} · ${relativeTime(medication.occurred_at, now)}`;
  return { ...base, value: medication.payload.drug_name, unit: "", sub, sparkline: null, present: true };
}

function attentionStat(entries: JournalEntryRead[]): JournalStat {
  const meta = ENTRY_TYPE_META.symptom;
  const base = {
    key: "attention" as const,
    label: "Needs attention",
    accentVar: meta.accentVar,
    iconType: "symptom" as EntryType,
  };
  const concerns = entries.filter((entry) => entry.is_concern);
  if (concerns.length === 0) {
    return { ...base, value: "0", unit: "flags", sub: "All clear", sparkline: null, present: false };
  }
  const latest = concerns[0];
  return {
    ...base,
    value: String(concerns.length),
    unit: concerns.length === 1 ? "flag" : "flags",
    sub: `${entryPresentation(latest).title} · ${shortDate(latest.occurred_at)}`,
    sparkline: null,
    present: true,
  };
}

export function computeJournalStats(
  entries: JournalEntryRead[],
  now: Date = new Date(),
): JournalStat[] {
  return [
    weightStat(entries),
    mealStat(entries, now),
    medicationStat(entries, now),
    attentionStat(entries),
  ];
}
