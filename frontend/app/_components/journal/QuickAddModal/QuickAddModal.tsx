"use client";

import { useEffect, useId, useRef, useState, type CSSProperties } from "react";
import {
  JournalError,
  createJournalEntry,
  updateJournalEntry,
} from "@/lib/journal";
import { ENTRY_TYPE_META, ENTRY_TYPES, type EntryType } from "@/lib/journal.constants";
import type {
  BathroomPayload,
  FreeNotePayload,
  JournalEntryRead,
  MealPayload,
  MedicationPayload,
  MoodPayload,
  SymptomPayload,
  VetVisitPayload,
  WeightPayload,
} from "@/lib/journal.schemas";
import { useFocusTrap } from "@/lib/useFocusTrap";
import {
  BathroomForm,
  FreeNoteForm,
  MealForm,
  MedicationForm,
  MoodForm,
  SymptomForm,
  VetVisitForm,
  WeightForm,
  type EntryDraft,
} from "./forms";
import styles from "./QuickAddModal.module.css";

const SUBMIT_LABELS: Record<EntryType, string> = {
  meal: "Log this meal",
  bathroom: "Save bathroom log",
  symptom: "Save symptom",
  mood: "Save mood",
  medication: "Log medication",
  weight: "Log weight",
  vet_visit: "Save visit",
  free_note: "Save note",
};

export type QuickAddSavedMode = "created" | "updated";

type QuickAddModalProps = {
  petId: string;
  petName: string;
  open: boolean;
  initialEntryType?: EntryType | null;
  entry?: JournalEntryRead | null;
  recentMeals?: MealPayload[];
  recentMedications?: MedicationPayload[];
  onClose: () => void;
  onSaved: (entry: JournalEntryRead, mode: QuickAddSavedMode) => void;
};

export function QuickAddModal(props: QuickAddModalProps) {
  if (!props.open) return null;
  return <QuickAddModalBody key={props.entry?.id ?? "create"} {...props} />;
}

function toDatetimeLocalValue(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function QuickAddModalBody({
  petId,
  petName,
  initialEntryType = null,
  entry = null,
  recentMeals,
  recentMedications,
  onClose,
  onSaved,
}: QuickAddModalProps) {
  const isEdit = entry !== null;
  const [entryType, setEntryType] = useState<EntryType | null>(
    isEdit ? (entry.payload.entry_type as EntryType) : (initialEntryType ?? null),
  );
  const [occurredAtLocal, setOccurredAtLocal] = useState(() =>
    toDatetimeLocalValue(isEdit ? new Date(entry.occurred_at) : new Date()),
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  useFocusTrap(dialogRef);
  const headingId = useId();
  const occurredAtId = useId();

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape" && !submitting) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [submitting, onClose]);

  async function handleSubmit(draft: EntryDraft) {
    setError(null);
    setSubmitting(true);
    const occurredAtIso = new Date(occurredAtLocal).toISOString();
    try {
      if (isEdit) {
        const updated = await updateJournalEntry(petId, entry.id, {
          payload: draft.payload,
          occurred_at: occurredAtIso,
          note: draft.note,
          tags: draft.tags,
        });
        onSaved(updated, "updated");
      } else {
        const created = await createJournalEntry(petId, {
          payload: draft.payload,
          occurred_at: occurredAtIso,
          note: draft.note,
          tags: draft.tags,
        });
        onSaved(created, "created");
      }
    } catch (caught) {
      setSubmitting(false);
      setError(saveErrorMessage(caught));
    }
  }

  const heading = entryType
    ? `${isEdit ? "Edit" : ""} ${ENTRY_TYPE_META[entryType].label}`.trim()
    : "What happened?";

  return (
    <div
      className={styles.backdrop}
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !submitting) onClose();
      }}
    >
      <div
        ref={dialogRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        className={styles.dialog}
      >
        <header className={styles.header}>
          <div>
            {entryType && (
              <span
                className={styles.headerEyebrow}
                style={{ color: `var(${ENTRY_TYPE_META[entryType].accentVar})` }}
              >
                {petName}
              </span>
            )}
            <h2 id={headingId} className={`${styles.heading} display`}>
              {heading}
            </h2>
          </div>
          <button
            type="button"
            className={styles.closeButton}
            onClick={onClose}
            disabled={submitting}
            aria-label="Close"
          >
            ×
          </button>
        </header>

        <div className={styles.content}>
          {entryType === null ? (
            <div className={styles.typeGrid}>
              {ENTRY_TYPES.map((type) => {
                const meta = ENTRY_TYPE_META[type];
                return (
                  <button
                    key={type}
                    type="button"
                    className={styles.typeTile}
                    style={{ "--entry-accent": `var(${meta.accentVar})` } as CSSProperties}
                    onClick={() => setEntryType(type)}
                  >
                    <span className={styles.typeTileLabel}>{meta.label}</span>
                    <span className={styles.typeTileSub}>{meta.subtitle}</span>
                  </button>
                );
              })}
            </div>
          ) : (
            <>
              {!isEdit && (
                <button
                  type="button"
                  className={styles.backButton}
                  onClick={() => setEntryType(null)}
                >
                  ← All types
                </button>
              )}
              <div className={styles.field}>
                <label className={styles.fieldLabel} htmlFor={occurredAtId}>
                  When
                </label>
                <input
                  id={occurredAtId}
                  type="datetime-local"
                  className={styles.textInput}
                  value={occurredAtLocal}
                  max={toDatetimeLocalValue(new Date())}
                  onChange={(event) => setOccurredAtLocal(event.target.value)}
                />
              </div>
              {renderForm({
                entryType,
                entry,
                recentMeals,
                recentMedications,
                submitting,
                onSubmit: handleSubmit,
              })}
              {error && (
                <p role="alert" className={styles.formError}>
                  {error}
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function saveErrorMessage(caught: unknown): string {
  if (caught instanceof JournalError) {
    if (caught.code === "JOURNAL_VALIDATION_ERROR") {
      return "Some fields look off — check the values and try again.";
    }
    if (caught.code === "ENTRY_NOT_FOUND" || caught.code === "PET_NOT_FOUND") {
      return "This entry no longer exists.";
    }
  }
  return "We couldn't save this entry. Try again in a moment.";
}

type RenderFormArgs = {
  entryType: EntryType;
  entry: JournalEntryRead | null;
  recentMeals?: MealPayload[];
  recentMedications?: MedicationPayload[];
  submitting: boolean;
  onSubmit: (draft: EntryDraft) => void;
};

function renderForm({
  entryType,
  entry,
  recentMeals,
  recentMedications,
  submitting,
  onSubmit,
}: RenderFormArgs) {
  const common = {
    initialTags: entry?.tags,
    initialNote: entry?.note,
    submitting,
    submitLabel: entry ? "Save changes" : SUBMIT_LABELS[entryType],
    onSubmit,
  };
  switch (entryType) {
    case "meal":
      return (
        <MealForm
          {...common}
          initialPayload={entry?.payload as MealPayload | undefined}
          recentMeals={recentMeals}
        />
      );
    case "bathroom":
      return (
        <BathroomForm {...common} initialPayload={entry?.payload as BathroomPayload | undefined} />
      );
    case "symptom":
      return (
        <SymptomForm {...common} initialPayload={entry?.payload as SymptomPayload | undefined} />
      );
    case "mood":
      return <MoodForm {...common} initialPayload={entry?.payload as MoodPayload | undefined} />;
    case "medication":
      return (
        <MedicationForm
          {...common}
          initialPayload={entry?.payload as MedicationPayload | undefined}
          recentMedications={recentMedications}
        />
      );
    case "weight":
      return (
        <WeightForm {...common} initialPayload={entry?.payload as WeightPayload | undefined} />
      );
    case "vet_visit":
      return (
        <VetVisitForm {...common} initialPayload={entry?.payload as VetVisitPayload | undefined} />
      );
    case "free_note":
      return (
        <FreeNoteForm {...common} initialPayload={entry?.payload as FreeNotePayload | undefined} />
      );
  }
}
