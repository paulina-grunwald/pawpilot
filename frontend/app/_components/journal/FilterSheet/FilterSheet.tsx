"use client";

import { useEffect, useId, useRef, type CSSProperties } from "react";
import { ENTRY_TYPE_META, ENTRY_TYPES, type EntryType } from "@/lib/journal.constants";
import { useFocusTrap } from "@/lib/useFocusTrap";
import { useRadioGroupNav } from "@/lib/useRadioGroupNav";
import styles from "./FilterSheet.module.css";

export type DateRangePreset = "today" | "7d" | "30d" | "all";

export type JournalFilters = {
  entryTypes: EntryType[];
  dateRange: DateRangePreset;
  concernsOnly: boolean;
};

export const DEFAULT_FILTERS: JournalFilters = {
  entryTypes: [],
  dateRange: "all",
  concernsOnly: false,
};

export function countActiveFilters(filters: JournalFilters): number {
  return (
    filters.entryTypes.length +
    (filters.dateRange !== "all" ? 1 : 0) +
    (filters.concernsOnly ? 1 : 0)
  );
}

export function toggleEntryTypeFilter(filters: JournalFilters, entryType: EntryType): JournalFilters {
  const active = filters.entryTypes.includes(entryType);
  return {
    ...filters,
    entryTypes: active
      ? filters.entryTypes.filter((existing) => existing !== entryType)
      : [...filters.entryTypes, entryType],
  };
}

export function dateRangeToOccurredFrom(
  preset: DateRangePreset,
  now: Date = new Date(),
): string | undefined {
  if (preset === "all") return undefined;
  const start = new Date(now);
  if (preset === "today") {
    start.setHours(0, 0, 0, 0);
  } else {
    start.setDate(start.getDate() - (preset === "7d" ? 7 : 30));
  }
  return start.toISOString();
}

const DATE_RANGE_OPTIONS: { value: DateRangePreset; label: string }[] = [
  { value: "today", label: "Today" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "30 days" },
  { value: "all", label: "All" },
];

type FilterSheetProps = {
  open: boolean;
  filters: JournalFilters;
  totalMatching: number | null;
  onChange: (filters: JournalFilters) => void;
  onClose: () => void;
};

export function FilterSheet(props: FilterSheetProps) {
  if (!props.open) return null;
  return <FilterSheetBody {...props} />;
}

function FilterSheetBody({ filters, totalMatching, onChange, onClose }: FilterSheetProps) {
  const dialogRef = useRef<HTMLDivElement | null>(null);
  useFocusTrap(dialogRef);
  const headingId = useId();
  const concernsId = useId();

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  function toggleEntryType(entryType: EntryType) {
    onChange(toggleEntryTypeFilter(filters, entryType));
  }

  const dateRangeItemProps = useRadioGroupNav(
    DATE_RANGE_OPTIONS.length,
    DATE_RANGE_OPTIONS.findIndex((option) => option.value === filters.dateRange),
    (index) => onChange({ ...filters, dateRange: DATE_RANGE_OPTIONS[index].value }),
  );

  return (
    <div
      className={styles.backdrop}
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        className={styles.sheet}
      >
        <div className={styles.headerRow}>
          <h2 id={headingId} className={`${styles.heading} display`}>
            Filter entries
          </h2>
          <button
            type="button"
            className={styles.resetButton}
            onClick={() => onChange(DEFAULT_FILTERS)}
          >
            Reset
          </button>
        </div>

        <fieldset className={styles.fieldset}>
          <legend className={styles.legend}>Date range</legend>
          <div className={styles.pillRow} role="radiogroup" aria-label="Date range">
            {DATE_RANGE_OPTIONS.map((option, index) => (
              <button
                key={option.value}
                type="button"
                role="radio"
                aria-checked={filters.dateRange === option.value}
                className={`${styles.pill} ${filters.dateRange === option.value ? styles.pillActive : ""}`}
                onClick={() => onChange({ ...filters, dateRange: option.value })}
                {...dateRangeItemProps(index)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className={styles.fieldset}>
          <legend className={styles.legend}>Entry types</legend>
          <div className={styles.pillRow}>
            {ENTRY_TYPES.map((entryType) => {
              const meta = ENTRY_TYPE_META[entryType];
              const active = filters.entryTypes.includes(entryType);
              return (
                <button
                  key={entryType}
                  type="button"
                  aria-pressed={active}
                  className={`${styles.typePill} ${active ? styles.typePillActive : ""}`}
                  style={{ "--entry-accent": `var(${meta.accentVar})` } as CSSProperties}
                  onClick={() => toggleEntryType(entryType)}
                >
                  {meta.label}
                </button>
              );
            })}
          </div>
        </fieldset>

        <div className={styles.toggleRow}>
          <label htmlFor={concernsId}>
            <span className={styles.toggleTitle}>Concerns only</span>
            <span className={styles.toggleHint}>Symptoms + flagged entries</span>
          </label>
          <input
            id={concernsId}
            type="checkbox"
            checked={filters.concernsOnly}
            onChange={(event) => onChange({ ...filters, concernsOnly: event.target.checked })}
          />
        </div>

        <button type="button" className={styles.applyButton} onClick={onClose}>
          {totalMatching === null
            ? "Show matching entries"
            : `Show ${totalMatching} matching ${totalMatching === 1 ? "entry" : "entries"}`}
        </button>
      </div>
    </div>
  );
}
