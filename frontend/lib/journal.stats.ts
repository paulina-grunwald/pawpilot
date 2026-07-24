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
  subtitle: string;
  sparkline: number[] | null;
  present: boolean;
};

const PLACEHOLDER = "—";

// A medication logged longer ago than this is no longer assumed to be an
// ongoing course — the card switches from "Active med" to "Last medication"
// rather than implying treatment that has likely ended.
const MEDICATION_ACTIVE_WINDOW_MS = 14 * 24 * 60 * 60 * 1000;

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

// Before the client has mounted (`now` is null), fall back to an absolute date
// instead of calling relativeTime with a fresh `new Date()` — that call would
// evaluate independently on the server and during client hydration and could
// render different text ("59m ago" vs "1h ago"), causing a hydration mismatch.
function recencyLabel(occurredAt: string, now: Date | null): string {
  return now ? relativeTime(occurredAt, now) : shortDate(occurredAt);
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
    return { ...base, value: PLACEHOLDER, unit: "kg", subtitle: "No weigh-ins yet", sparkline: null, present: false };
  }
  // entries are newest-first; oldest is last, chronological runs oldest -> newest.
  const newest = weights[0].payload.weight_grams;
  const oldest = weights[weights.length - 1].payload.weight_grams;
  const sparkline = weights.map((entry) => entry.payload.weight_grams).reverse();
  let subtitle = "First reading logged";
  if (weights.length > 1) {
    const deltaKg = (newest - oldest) / 1000;
    const magnitude = Math.abs(deltaKg).toFixed(1);
    if (magnitude === "0.0") {
      subtitle = "Steady over recent logs";
    } else {
      subtitle = `${deltaKg < 0 ? "↓" : "↑"} ${magnitude} kg recently`;
    }
  }
  return { ...base, value: weightKg(newest), unit: "kg", subtitle, sparkline, present: true };
}

function mealStat(entries: JournalEntryRead[], now: Date | null): JournalStat {
  const meta = ENTRY_TYPE_META.meal;
  const base = { key: "meal" as const, label: "Last meal", accentVar: meta.accentVar, iconType: "meal" as EntryType };
  const meal = entries.find((entry) => entry.payload.entry_type === "meal");
  if (!meal || meal.payload.entry_type !== "meal") {
    return { ...base, value: PLACEHOLDER, unit: "", subtitle: "No meals logged", sparkline: null, present: false };
  }
  const grams = meal.payload.amount_grams;
  return {
    ...base,
    value: grams !== null ? String(grams) : meal.payload.food_name,
    unit: grams !== null ? "g" : "",
    subtitle: `${meal.payload.food_name} · ${recencyLabel(meal.occurred_at, now)}`,
    sparkline: null,
    present: true,
  };
}

function medicationStat(entries: JournalEntryRead[], now: Date | null): JournalStat {
  const meta = ENTRY_TYPE_META.medication;
  const base = { key: "medication" as const, accentVar: meta.accentVar, iconType: "medication" as EntryType };
  const medication = entries.find((entry) => entry.payload.entry_type === "medication");
  if (!medication || medication.payload.entry_type !== "medication") {
    return {
      ...base,
      label: "Active med",
      value: PLACEHOLDER,
      unit: "",
      subtitle: "No active meds",
      sparkline: null,
      present: false,
    };
  }
  const recency = recencyLabel(medication.occurred_at, now);
  const elapsedMs = now ? now.getTime() - new Date(medication.occurred_at).getTime() : 0;
  const isStale = now !== null && elapsedMs > MEDICATION_ACTIVE_WINDOW_MS;
  const label = isStale && !medication.payload.missed_dose ? "Last medication" : "Active med";
  const subtitle = medication.payload.missed_dose ? `Missed · ${recency}` : `${medication.payload.dose} · ${recency}`;
  return { ...base, label, value: medication.payload.drug_name, unit: "", subtitle, sparkline: null, present: true };
}

function attentionStat(entries: JournalEntryRead[]): JournalStat {
  const label = "Needs attention";
  const concerns = entries.filter((entry) => entry.is_concern);
  if (concerns.length === 0) {
    const meta = ENTRY_TYPE_META.symptom;
    return {
      key: "attention",
      label,
      accentVar: meta.accentVar,
      iconType: "symptom",
      value: "0",
      unit: "flags",
      subtitle: "All clear",
      sparkline: null,
      present: false,
    };
  }
  const latest = concerns[0];
  // Icon/accent reflect the entry type that actually triggered the concern
  // (bathroom, medication, mood, or symptom) rather than always the symptom
  // icon, since compute_is_concern flags all four entry types.
  const latestType = latest.payload.entry_type as EntryType;
  const meta = ENTRY_TYPE_META[latestType];
  return {
    key: "attention",
    label,
    accentVar: meta.accentVar,
    iconType: latestType,
    value: String(concerns.length),
    unit: concerns.length === 1 ? "flag" : "flags",
    subtitle: `${entryPresentation(latest).title} · ${shortDate(latest.occurred_at)}`,
    sparkline: null,
    present: true,
  };
}

export function computeJournalStats(entries: JournalEntryRead[], now: Date | null): JournalStat[] {
  return [
    weightStat(entries),
    mealStat(entries, now),
    medicationStat(entries, now),
    attentionStat(entries),
  ];
}
