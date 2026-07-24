import {
  ENTRY_TYPE_META,
  MEAL_CATEGORY_LABELS,
  MOOD_LABELS,
  SEVERITY_LABELS,
  WEIGHT_SOURCE_LABELS,
  type EntryType,
} from "./journal.constants";
import type { JournalEntryRead } from "./journal.schemas";

export type EntryPresentation = {
  title: string;
  meta: string | null;
  value: string | null;
};

export function formatKg(weightGrams: number): string {
  return `${(weightGrams / 1000).toFixed(1)} kg`;
}

export function kgToGrams(weightKg: number): number {
  return Math.round(weightKg * 1000);
}

export function gramsToKg(weightGrams: number): number {
  return Math.round(weightGrams / 100) / 10;
}

export function entryPresentation(entry: JournalEntryRead): EntryPresentation {
  const payload = entry.payload;
  switch (payload.entry_type) {
    case "meal": {
      const categoryLabel = MEAL_CATEGORY_LABELS[payload.category];
      return {
        title: payload.food_name,
        meta: [categoryLabel, payload.brand].filter(Boolean).join(" · ") || null,
        value: payload.amount_grams !== null ? `${payload.amount_grams} g` : null,
      };
    }
    case "bathroom": {
      if (payload.kind === "pee") {
        return { title: "Pee only", meta: null, value: null };
      }
      const kindLabel = payload.kind === "both" ? "Poop + pee" : "Poop";
      const details = [
        payload.bristol_score !== null ? `type ${payload.bristol_score}` : null,
        payload.color,
      ]
        .filter(Boolean)
        .join(" · ");
      return {
        title: details ? `${kindLabel} · ${details}` : kindLabel,
        meta: entry.is_concern ? "Worth watching" : "Healthy log",
        value: null,
      };
    }
    case "symptom": {
      const severityLabel = SEVERITY_LABELS[payload.severity];
      return {
        title: entry.tags.length > 0 ? entry.tags.join(", ") : "Symptom",
        meta: [
          `${payload.severity}/5 · ${severityLabel}`,
          payload.body_area ? `area: ${payload.body_area}` : null,
        ]
          .filter(Boolean)
          .join(" · "),
        value: null,
      };
    }
    case "mood": {
      return {
        title: `${MOOD_LABELS[payload.score]} · ${payload.score}/5`,
        meta: null,
        value: null,
      };
    }
    case "medication": {
      return {
        title: `${payload.drug_name} · ${payload.dose}`,
        meta: payload.missed_dose ? "Missed dose" : null,
        value: null,
      };
    }
    case "weight": {
      return {
        title: "Weight check",
        meta: WEIGHT_SOURCE_LABELS[payload.source],
        value: formatKg(payload.weight_grams),
      };
    }
    case "vet_visit": {
      return {
        title: [payload.reason, payload.vet_name].filter(Boolean).join(" · "),
        meta:
          [payload.diagnosis, payload.follow_up ? `Follow-up: ${payload.follow_up}` : null]
            .filter(Boolean)
            .join(" · ") || null,
        value: null,
      };
    }
    case "free_note": {
      return { title: payload.text, meta: null, value: null };
    }
  }
}

export function entryTypeLabel(entryType: EntryType): string {
  return ENTRY_TYPE_META[entryType].label;
}

export function formatEntryTime(occurredAt: string): string {
  return new Date(occurredAt).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
}

export type DayGroup = {
  dayKey: string;
  label: string;
  isToday: boolean;
  entries: JournalEntryRead[];
};

function dayKeyOf(occurredAt: string): string {
  const date = new Date(occurredAt);
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function dayLabelOf(occurredAt: string, todayKey: string, yesterdayKey: string): string {
  const key = dayKeyOf(occurredAt);
  if (key === todayKey) return "Today";
  const formatted = new Date(occurredAt).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  if (key === yesterdayKey) return `Yesterday · ${formatted}`;
  return formatted;
}

export function groupEntriesByDay(entries: JournalEntryRead[], now: Date = new Date()): DayGroup[] {
  const todayKey = dayKeyOf(now.toISOString());
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayKey = dayKeyOf(yesterday.toISOString());

  const groups: DayGroup[] = [];
  for (const entry of entries) {
    const dayKey = dayKeyOf(entry.occurred_at);
    const lastGroup = groups[groups.length - 1];
    if (lastGroup && lastGroup.dayKey === dayKey) {
      lastGroup.entries.push(entry);
    } else {
      groups.push({
        dayKey,
        label: dayLabelOf(entry.occurred_at, todayKey, yesterdayKey),
        isToday: dayKey === todayKey,
        entries: [entry],
      });
    }
  }
  return groups;
}
