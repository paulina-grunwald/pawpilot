"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  deleteJournalEntry,
  listJournalEntries,
  type JournalListParams,
} from "@/lib/journal";
import { ENTRY_TYPE_META, type EntryType } from "@/lib/journal.constants";
import { groupEntriesByDay } from "@/lib/journal.format";
import type {
  JournalEntryListResponse,
  JournalEntryRead,
  MealPayload,
  MedicationPayload,
} from "@/lib/journal.schemas";
import { EntryCard } from "../EntryCard";
import {
  DEFAULT_FILTERS,
  FilterSheet,
  countActiveFilters,
  dateRangeToOccurredFrom,
  type JournalFilters,
} from "../FilterSheet";
import { QuickAddModal, type QuickAddSavedMode } from "../QuickAddModal";
import styles from "./JournalTimeline.module.css";

const PAGE_SIZE = 50;
const SEARCH_DEBOUNCE_MS = 300;
const UNDO_TOAST_MS = 6000;

type ModalState =
  | { kind: "closed" }
  | { kind: "create"; initialType: EntryType | null }
  | { kind: "edit"; entry: JournalEntryRead };

type ToastState = {
  message: string;
  undoEntryId: string | null;
};

type JournalTimelineProps = {
  petId: string;
  petName: string;
  initialPage: JournalEntryListResponse;
};

function sortNewestFirst(entries: JournalEntryRead[]): JournalEntryRead[] {
  return [...entries].sort((first, second) =>
    second.occurred_at.localeCompare(first.occurred_at),
  );
}

function queryParamsFor(
  search: string,
  filters: JournalFilters,
): JournalListParams {
  return {
    entryTypes: filters.entryTypes.length > 0 ? filters.entryTypes : undefined,
    occurredFrom: dateRangeToOccurredFrom(filters.dateRange),
    concernsOnly: filters.concernsOnly || undefined,
    search: search.trim() || undefined,
    limit: PAGE_SIZE,
  };
}

export function JournalTimeline({ petId, petName, initialPage }: JournalTimelineProps) {
  const [entries, setEntries] = useState<JournalEntryRead[]>(initialPage.items);
  const [nextCursor, setNextCursor] = useState(initialPage.next_cursor);
  const [totalMatching, setTotalMatching] = useState(initialPage.total_matching);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<JournalFilters>(DEFAULT_FILTERS);
  const [filterSheetOpen, setFilterSheetOpen] = useState(false);
  const [modal, setModal] = useState<ModalState>({ kind: "closed" });
  const [toast, setToast] = useState<ToastState | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const skipNextRefetch = useRef(true);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setListError(null);
    try {
      const page = await listJournalEntries(petId, queryParamsFor(search, filters));
      setEntries(page.items);
      setNextCursor(page.next_cursor);
      setTotalMatching(page.total_matching);
    } catch {
      setListError("We couldn't load the journal. Try again in a moment.");
    } finally {
      setLoading(false);
    }
  }, [petId, search, filters]);

  useEffect(() => {
    if (skipNextRefetch.current) {
      skipNextRefetch.current = false;
      return;
    }
    const timer = setTimeout(refetch, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [refetch]);

  useEffect(() => {
    return () => {
      if (toastTimer.current) clearTimeout(toastTimer.current);
    };
  }, []);

  function showToast(nextToast: ToastState) {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast(nextToast);
    toastTimer.current = setTimeout(() => setToast(null), UNDO_TOAST_MS);
  }

  function handleSaved(entry: JournalEntryRead, mode: QuickAddSavedMode) {
    setModal({ kind: "closed" });
    if (mode === "created") {
      setEntries((current) => sortNewestFirst([entry, ...current]));
      setTotalMatching((current) => current + 1);
      showToast({
        message: `${ENTRY_TYPE_META[entry.payload.entry_type as EntryType].label} logged`,
        undoEntryId: entry.id,
      });
    } else {
      setEntries((current) =>
        sortNewestFirst(current.map((existing) => (existing.id === entry.id ? entry : existing))),
      );
      showToast({ message: "Entry updated", undoEntryId: null });
    }
  }

  async function handleUndo(entryId: string) {
    setToast(null);
    try {
      await deleteJournalEntry(petId, entryId);
      setEntries((current) => current.filter((entry) => entry.id !== entryId));
      setTotalMatching((current) => Math.max(0, current - 1));
    } catch {
      showToast({ message: "Couldn't undo — the entry is still saved.", undoEntryId: null });
    }
  }

  async function handleDelete(entry: JournalEntryRead) {
    try {
      await deleteJournalEntry(petId, entry.id);
      setEntries((current) => current.filter((existing) => existing.id !== entry.id));
      setTotalMatching((current) => Math.max(0, current - 1));
      showToast({ message: "Entry deleted", undoEntryId: null });
    } catch {
      showToast({ message: "Couldn't delete this entry.", undoEntryId: null });
    }
  }

  async function handleLoadMore() {
    if (!nextCursor) return;
    setLoadingMore(true);
    try {
      const page = await listJournalEntries(petId, {
        ...queryParamsFor(search, filters),
        cursor: nextCursor,
      });
      setEntries((current) => [...current, ...page.items]);
      setNextCursor(page.next_cursor);
    } catch {
      setListError("We couldn't load more entries.");
    } finally {
      setLoadingMore(false);
    }
  }

  const recentMeals = useMemo<MealPayload[]>(() => {
    const seen = new Set<string>();
    const meals: MealPayload[] = [];
    for (const entry of entries) {
      if (entry.payload.entry_type !== "meal") continue;
      if (seen.has(entry.payload.food_name)) continue;
      seen.add(entry.payload.food_name);
      meals.push(entry.payload);
      if (meals.length === 5) break;
    }
    return meals;
  }, [entries]);

  const recentMedications = useMemo<MedicationPayload[]>(() => {
    const seen = new Set<string>();
    const medications: MedicationPayload[] = [];
    for (const entry of entries) {
      if (entry.payload.entry_type !== "medication") continue;
      const key = `${entry.payload.drug_name}|${entry.payload.dose}`;
      if (seen.has(key)) continue;
      seen.add(key);
      medications.push(entry.payload);
      if (medications.length === 5) break;
    }
    return medications;
  }, [entries]);

  const activeFilterCount = countActiveFilters(filters);
  const hasActiveQuery = activeFilterCount > 0 || search.trim().length > 0;
  const dayGroups = groupEntriesByDay(entries);
  const showEmptyState = entries.length === 0 && !hasActiveQuery && !loading;

  return (
    <section className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={`${styles.title} display`}>{petName}&rsquo;s journal</h1>
          <p className={styles.subtitle}>
            {totalMatching === 1 ? "1 entry" : `${totalMatching} entries`}
          </p>
        </div>
      </header>

      {!showEmptyState && (
        <div className={styles.toolbar}>
          <input
            type="search"
            className={styles.searchInput}
            placeholder="Search notes & tags…"
            aria-label="Search notes and tags"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <button
            type="button"
            className={`${styles.filterButton} ${activeFilterCount > 0 ? styles.filterButtonActive : ""}`}
            onClick={() => setFilterSheetOpen(true)}
          >
            {activeFilterCount > 0 ? `Filters · ${activeFilterCount}` : "Filter"}
          </button>
        </div>
      )}

      {listError && (
        <p role="alert" className={styles.error}>
          {listError}
        </p>
      )}

      {showEmptyState ? (
        <EmptyState
          petName={petName}
          onStart={(entryType) => setModal({ kind: "create", initialType: entryType })}
        />
      ) : (
        <div className={styles.feed} aria-busy={loading}>
          {dayGroups.map((group) => (
            <section key={group.dayKey} aria-label={group.label}>
              <div className={styles.dayRow}>
                <h2 className={`${styles.dayLabel} display`}>{group.label}</h2>
                <span className={styles.dayCount}>
                  {group.entries.length === 1 ? "1 entry" : `${group.entries.length} entries`}
                </span>
              </div>
              <div className={styles.dayEntries}>
                {group.entries.map((entry) => (
                  <EntryCard
                    key={entry.id}
                    entry={entry}
                    onEdit={(target) => setModal({ kind: "edit", entry: target })}
                    onDelete={handleDelete}
                  />
                ))}
              </div>
            </section>
          ))}
          {entries.length === 0 && hasActiveQuery && !loading && (
            <p className={styles.noMatches}>No entries match — try widening the filters.</p>
          )}
          {nextCursor && (
            <button
              type="button"
              className={styles.loadMoreButton}
              onClick={handleLoadMore}
              disabled={loadingMore}
            >
              {loadingMore ? "Loading…" : "Load older entries"}
            </button>
          )}
        </div>
      )}

      <button
        type="button"
        className={styles.fab}
        onClick={() => setModal({ kind: "create", initialType: null })}
      >
        + Log
      </button>

      {toast && (
        <div className={styles.toast} role="status">
          <span>{toast.message}</span>
          {toast.undoEntryId && (
            <button
              type="button"
              className={styles.undoButton}
              onClick={() => handleUndo(toast.undoEntryId as string)}
            >
              Undo
            </button>
          )}
        </div>
      )}

      <FilterSheet
        open={filterSheetOpen}
        filters={filters}
        totalMatching={loading ? null : totalMatching}
        onChange={setFilters}
        onClose={() => setFilterSheetOpen(false)}
      />

      <QuickAddModal
        petId={petId}
        petName={petName}
        open={modal.kind !== "closed"}
        initialEntryType={modal.kind === "create" ? modal.initialType : null}
        entry={modal.kind === "edit" ? modal.entry : null}
        recentMeals={recentMeals}
        recentMedications={recentMedications}
        onClose={() => setModal({ kind: "closed" })}
        onSaved={handleSaved}
      />
    </section>
  );
}

const STARTERS: { entryType: EntryType; label: string; sub: string }[] = [
  { entryType: "meal", label: "Add your first meal", sub: "What did they eat today?" },
  { entryType: "mood", label: "Log their mood", sub: "A tap is enough" },
  { entryType: "symptom", label: "Note a symptom", sub: "Anything off?" },
];

function EmptyState({
  petName,
  onStart,
}: {
  petName: string;
  onStart: (entryType: EntryType) => void;
}) {
  return (
    <div className={styles.emptyState}>
      <h2 className={`${styles.emptyTitle} display`}>{petName}&rsquo;s journal is empty.</h2>
      <p className={styles.emptyBody}>
        Logging meals, mood, and symptoms helps PawPilot spot when something&rsquo;s off — before
        it becomes a vet visit.
      </p>
      <div className={styles.starterList}>
        {STARTERS.map((starter) => (
          <button
            key={starter.entryType}
            type="button"
            className={styles.starterButton}
            onClick={() => onStart(starter.entryType)}
          >
            <span className={styles.starterLabel}>{starter.label}</span>
            <span className={styles.starterSub}>{starter.sub}</span>
          </button>
        ))}
      </div>
      <p className={styles.emptyHint}>
        <strong>3 entries</strong> is enough for PawPilot to start noticing patterns. Most owners
        log <strong>5–8 a day</strong>.
      </p>
    </div>
  );
}
