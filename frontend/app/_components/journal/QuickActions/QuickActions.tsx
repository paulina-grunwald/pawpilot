"use client";

import Link from "next/link";
import { useState } from "react";
import type { EntryType } from "@/lib/journal.constants";
import { QuickAddModal } from "../QuickAddModal";
import styles from "./QuickActions.module.css";

const ACTIONS: { entryType: EntryType; label: string }[] = [
  { entryType: "meal", label: "Log meal" },
  { entryType: "bathroom", label: "Log bathroom" },
  { entryType: "symptom", label: "Note symptom" },
  { entryType: "mood", label: "Log mood" },
];

type QuickActionsProps = {
  petId: string;
  petName: string;
};

export function QuickActions({ petId, petName }: QuickActionsProps) {
  const [openType, setOpenType] = useState<EntryType | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  function openFor(entryType: EntryType | null) {
    setSavedMessage(null);
    setOpenType(entryType);
    setModalOpen(true);
  }

  return (
    <section aria-label="Quick journal actions" className={styles.row}>
      {ACTIONS.map((action) => (
        <button
          key={action.entryType}
          type="button"
          className={styles.actionButton}
          onClick={() => openFor(action.entryType)}
        >
          {action.label}
        </button>
      ))}
      <button type="button" className={styles.actionButton} onClick={() => openFor(null)}>
        More…
      </button>
      <Link href={`/pets/${petId}/journal`} className={styles.journalLink}>
        Journal →
      </Link>
      {savedMessage && (
        <span role="status" className={styles.savedMessage}>
          {savedMessage}
        </span>
      )}
      <QuickAddModal
        petId={petId}
        petName={petName}
        open={modalOpen}
        initialEntryType={openType}
        onClose={() => setModalOpen(false)}
        onSaved={() => {
          setModalOpen(false);
          setSavedMessage("Logged ✓");
        }}
      />
    </section>
  );
}
