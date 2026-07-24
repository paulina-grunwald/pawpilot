"use client";

import type { CSSProperties } from "react";
import { ENTRY_TYPE_META, ENTRY_TYPES, type EntryType } from "@/lib/journal.constants";
import { toggleEntryTypeFilter, type JournalFilters } from "../FilterSheet";
import styles from "./FilterChips.module.css";

type FilterChipsProps = {
  filters: JournalFilters;
  onChange: (filters: JournalFilters) => void;
};

export function FilterChips({ filters, onChange }: FilterChipsProps) {
  const allActive = filters.entryTypes.length === 0;

  function selectAll() {
    if (allActive) return;
    onChange({ ...filters, entryTypes: [] });
  }

  function toggleType(entryType: EntryType) {
    onChange(toggleEntryTypeFilter(filters, entryType));
  }

  return (
    <div className={styles.row} role="group" aria-label="Filter by entry type">
      <button
        type="button"
        aria-pressed={allActive}
        className={`${styles.chip} ${allActive ? styles.active : ""}`}
        style={{ "--chip-accent": "var(--ink)" } as CSSProperties}
        onClick={selectAll}
      >
        <span className={styles.dot} />
        All
      </button>
      {ENTRY_TYPES.map((entryType) => {
        const meta = ENTRY_TYPE_META[entryType];
        const active = filters.entryTypes.includes(entryType);
        return (
          <button
            key={entryType}
            type="button"
            aria-pressed={active}
            className={`${styles.chip} ${active ? styles.active : ""}`}
            style={{ "--chip-accent": `var(${meta.accentVar})` } as CSSProperties}
            onClick={() => toggleType(entryType)}
          >
            <span className={styles.dot} />
            {meta.label}
          </button>
        );
      })}
    </div>
  );
}
