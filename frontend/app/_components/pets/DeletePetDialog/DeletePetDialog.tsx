"use client";

import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { PetsError, deletePet } from "@/lib/pets";
import styles from "./DeletePetDialog.module.css";

type DeletePetDialogProps = {
  open: boolean;
  petId: string;
  petName: string;
  onClose: () => void;
};

export function DeletePetDialog({ open, petId, petName, onClose }: DeletePetDialogProps) {
  if (!open) return null;
  return <DeletePetDialogBody petId={petId} petName={petName} onClose={onClose} />;
}

type DialogBodyProps = {
  petId: string;
  petName: string;
  onClose: () => void;
};

function DeletePetDialogBody({ petId, petName, onClose }: DialogBodyProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const headingId = useId();
  const inputId = useId();
  const errorId = useId();
  const [confirmation, setConfirmation] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape" && !isDeleting) {
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isDeleting, onClose]);

  const trimmed = confirmation.trim().toLowerCase();
  const target = petName.trim().toLowerCase();
  const canDelete = trimmed.length > 0 && trimmed === target && !isDeleting;

  async function handleDelete() {
    if (!canDelete) return;
    setError(null);
    setIsDeleting(true);
    try {
      await deletePet(petId);
      router.replace("/dashboard");
      router.refresh();
    } catch (caught) {
      setIsDeleting(false);
      setError(
        caught instanceof PetsError && caught.code === "PET_NOT_FOUND"
          ? "This pet no longer exists."
          : "We couldn't delete this pet. Try again in a moment.",
      );
    }
  }

  return (
    <div
      className={styles.backdrop}
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isDeleting) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        aria-describedby={error ? errorId : undefined}
        className={styles.dialog}
      >
        <h2 id={headingId} className={`${styles.heading} display`}>
          Delete {petName}?
        </h2>
        <p className={styles.body}>
          This removes the pet record and any uploaded photo. There&rsquo;s no undo.
        </p>

        <label htmlFor={inputId} className={styles.label}>
          Type <strong>{petName}</strong> to confirm
        </label>
        <input
          id={inputId}
          ref={inputRef}
          type="text"
          autoComplete="off"
          className={styles.input}
          value={confirmation}
          onChange={(event) => setConfirmation(event.target.value)}
          aria-invalid={error ? "true" : undefined}
          aria-describedby={error ? errorId : undefined}
        />

        {error && (
          <p id={errorId} role="alert" className={styles.error}>
            {error}
          </p>
        )}

        <div className={styles.actions}>
          <button
            type="button"
            onClick={onClose}
            disabled={isDeleting}
            className={styles.cancelButton}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={!canDelete}
            className={styles.deleteButton}
          >
            {isDeleting ? "Deleting…" : "Delete forever"}
          </button>
        </div>
      </div>
    </div>
  );
}
