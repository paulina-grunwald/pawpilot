"use client";

import { memo, useState, type CSSProperties } from "react";
import { ENTRY_TYPE_META, type EntryType } from "@/lib/journal.constants";
import { entryPresentation, entryTypeLabel, formatEntryTime } from "@/lib/journal.format";
import type { JournalEntryRead } from "@/lib/journal.schemas";
import styles from "./EntryCard.module.css";

type EntryCardProps = {
  entry: JournalEntryRead;
  onEdit?: (entry: JournalEntryRead) => void;
  onDelete?: (entry: JournalEntryRead) => void;
};

export const EntryCard = memo(function EntryCard({ entry, onEdit, onDelete }: EntryCardProps) {
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const entryType = entry.payload.entry_type as EntryType;
  const meta = ENTRY_TYPE_META[entryType];
  const presentation = entryPresentation(entry);
  const accentStyle = { "--entry-accent": `var(${meta.accentVar})` } as CSSProperties;

  function handleDeleteClick() {
    if (!confirmingDelete) {
      setConfirmingDelete(true);
      return;
    }
    setConfirmingDelete(false);
    onDelete?.(entry);
  }

  return (
    <article
      className={`${styles.card} ${entry.is_concern ? styles.concern : ""}`}
      style={accentStyle}
      aria-label={`${entryTypeLabel(entryType)} entry`}
    >
      <div className={styles.body}>
        <div className={styles.topRow}>
          <span className={styles.typeLabel}>{entryTypeLabel(entryType)}</span>
          <time className={styles.time} dateTime={entry.occurred_at}>
            {formatEntryTime(entry.occurred_at)}
          </time>
        </div>
        <div className={styles.titleRow}>
          <span className={styles.title}>{presentation.title}</span>
          {presentation.value && <span className={styles.value}>{presentation.value}</span>}
        </div>
        {presentation.meta && <p className={styles.meta}>{presentation.meta}</p>}
        {entry.note && <p className={styles.note}>{entry.note}</p>}
        {entry.is_concern && <span className={styles.concernPill}>Needs attention</span>}
        {entry.tags.length > 0 && entryType !== "symptom" && (
          <div className={styles.tags}>
            {entry.tags.map((tag) => (
              <span key={tag} className={styles.tag}>
                {tag}
              </span>
            ))}
          </div>
        )}
        {(onEdit || onDelete) && (
          <div className={styles.actions}>
            {onEdit && (
              <button type="button" className={styles.actionButton} onClick={() => onEdit(entry)}>
                Edit
              </button>
            )}
            {onDelete && (
              <button
                type="button"
                className={`${styles.actionButton} ${styles.deleteButton}`}
                onClick={handleDeleteClick}
                onBlur={() => setConfirmingDelete(false)}
              >
                {confirmingDelete ? "Confirm delete" : "Delete"}
              </button>
            )}
          </div>
        )}
      </div>
      {entry.photo_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img className={styles.photo} src={entry.photo_url} alt="Entry photo" />
      )}
    </article>
  );
});
