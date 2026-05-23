"use client";

import { useEffect, useId, useRef, useState, type ChangeEvent, type DragEvent } from "react";
import styles from "./PhotoUploader.module.css";

const ACCEPTED_MIMES = ["image/png", "image/jpeg", "image/webp"] as const;
const ACCEPTED_ATTR = ACCEPTED_MIMES.join(",");
const MAX_BYTES = 5 * 1024 * 1024;

type PhotoUploaderError =
  | { type: "mime"; message: string }
  | { type: "size"; message: string };

type PhotoUploaderProps = {
  existingPhotoUrl?: string | null;
  file: File | null;
  removeRequested?: boolean;
  onFileChange: (file: File | null) => void;
  onRemoveExisting?: () => void;
  altText?: string;
};

export function PhotoUploader({
  existingPhotoUrl,
  file,
  removeRequested = false,
  onFileChange,
  onRemoveExisting,
  altText = "Pet photo preview",
}: PhotoUploaderProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const inputId = useId();
  const [error, setError] = useState<PhotoUploaderError | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [localPreview, setLocalPreview] = useState<string | null>(null);

  useEffect(() => {
    if (!file) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLocalPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setLocalPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const previewUrl = localPreview ?? (removeRequested ? null : existingPhotoUrl ?? null);

  function validate(candidate: File): PhotoUploaderError | null {
    if (!ACCEPTED_MIMES.includes(candidate.type as (typeof ACCEPTED_MIMES)[number])) {
      return {
        type: "mime",
        message: "Use a PNG, JPG, or WEBP file.",
      };
    }
    if (candidate.size > MAX_BYTES) {
      return {
        type: "size",
        message: "Image must be 5 MB or smaller.",
      };
    }
    return null;
  }

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    const next = files[0];
    const validation = validate(next);
    if (validation) {
      setError(validation);
      return;
    }
    setError(null);
    onFileChange(next);
  }

  function onInputChange(event: ChangeEvent<HTMLInputElement>) {
    handleFiles(event.target.files);
    event.target.value = "";
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragActive(false);
    handleFiles(event.dataTransfer.files);
  }

  function onDragOver(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    if (!dragActive) setDragActive(true);
  }

  function onDragLeave(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragActive(false);
  }

  function clearLocalPick() {
    setError(null);
    onFileChange(null);
  }

  function requestRemoveExisting() {
    setError(null);
    onRemoveExisting?.();
  }

  const dropzoneClasses = `${styles.dropzone} ${dragActive ? styles.dropzoneActive : ""}`;
  const hasLocalFile = file !== null;
  const showRemoveExistingButton =
    !hasLocalFile && existingPhotoUrl && !removeRequested && onRemoveExisting !== undefined;

  return (
    <div>
      <div className={styles.wrapper}>
        <div className={styles.preview}>
          {previewUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img className={styles.previewImage} src={previewUrl} alt={altText} />
          ) : (
            <span className={styles.previewPlaceholder}>No photo</span>
          )}
        </div>

        <label
          htmlFor={inputId}
          className={dropzoneClasses}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
        >
          <span className={styles.dropzonePrimary}>
            {hasLocalFile ? "Picked a new photo" : "Drop a photo here or click to pick"}
          </span>
          <span className={styles.dropzoneHint}>PNG, JPG, or WEBP · up to 5 MB</span>
          <input
            ref={inputRef}
            id={inputId}
            type="file"
            accept={ACCEPTED_ATTR}
            className={styles.hiddenInput}
            onChange={onInputChange}
            aria-label="Pet photo"
          />
        </label>
      </div>

      {(hasLocalFile || showRemoveExistingButton) && (
        <div className={styles.actionsRow}>
          {hasLocalFile && (
            <button type="button" className={styles.removeButton} onClick={clearLocalPick}>
              Discard pick
            </button>
          )}
          {showRemoveExistingButton && (
            <button
              type="button"
              className={styles.removeButton}
              onClick={requestRemoveExisting}
            >
              Remove current photo
            </button>
          )}
        </div>
      )}

      {error && (
        <p role="alert" className={styles.error}>
          {error.message}
        </p>
      )}
    </div>
  );
}
