"use client";

import {
  useEffect,
  useId,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
} from "react";
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
  const [error, setError] = useState<PhotoUploaderError | null>(null);
  const [localPreview, setLocalPreview] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

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
  const hasLocalFile = file !== null;
  const hasExistingVisible = !!existingPhotoUrl && !removeRequested;
  const hasAnyPreview = hasLocalFile || hasExistingVisible;
  const showRemoveExistingButton =
    !hasLocalFile && hasExistingVisible && onRemoveExisting !== undefined;

  function validateFile(candidate: File): PhotoUploaderError | null {
    if (!ACCEPTED_MIMES.includes(candidate.type as (typeof ACCEPTED_MIMES)[number])) {
      return { type: "mime", message: "Use a PNG, JPG, or WEBP file." };
    }
    if (candidate.size > MAX_BYTES) {
      return { type: "size", message: "Image must be 5 MB or smaller." };
    }
    return null;
  }

  function acceptFiles(files: FileList | null): boolean {
    if (!files || files.length === 0) return false;
    const next = files[0];
    const validation = validateFile(next);
    if (validation) {
      setError(validation);
      return false;
    }
    setError(null);
    onFileChange(next);
    return true;
  }

  function clearLocalPick() {
    setError(null);
    onFileChange(null);
  }

  function requestRemoveExisting() {
    setError(null);
    onRemoveExisting?.();
  }

  function openModal() {
    setError(null);
    setIsModalOpen(true);
  }

  function closeModal() {
    setError(null);
    setIsModalOpen(false);
  }

  function handleFilesFromModal(files: FileList | null) {
    if (acceptFiles(files)) setIsModalOpen(false);
  }

  return (
    <div>
      <div className={styles.preview}>
        {previewUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img className={styles.previewImage} src={previewUrl} alt={altText} />
        ) : (
          <span className={styles.previewPlaceholder}>No photo</span>
        )}
      </div>

      <div className={styles.actionsRow}>
        <button
          type="button"
          className={styles.actionButton}
          onClick={openModal}
        >
          {hasAnyPreview ? "Change photo" : "Add photo"}
        </button>
        {hasLocalFile && (
          <button
            type="button"
            className={styles.removeButton}
            onClick={clearLocalPick}
          >
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

      <PhotoUploadModal
        open={isModalOpen}
        error={error}
        onFiles={handleFilesFromModal}
        onClose={closeModal}
      />
    </div>
  );
}

type PhotoUploadModalProps = {
  open: boolean;
  error: PhotoUploaderError | null;
  onFiles: (files: FileList | null) => void;
  onClose: () => void;
};

function PhotoUploadModal({ open, error, onFiles, onClose }: PhotoUploadModalProps) {
  if (!open) return null;
  return <PhotoUploadModalBody error={error} onFiles={onFiles} onClose={onClose} />;
}

type PhotoUploadModalBodyProps = Omit<PhotoUploadModalProps, "open">;

function PhotoUploadModalBody({ error, onFiles, onClose }: PhotoUploadModalBodyProps) {
  const inputId = useId();
  const headingId = useId();
  const errorId = useId();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  function onInputChange(event: ChangeEvent<HTMLInputElement>) {
    onFiles(event.target.files);
    event.target.value = "";
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragActive(false);
    onFiles(event.dataTransfer.files);
  }

  function onDragOver(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    if (!dragActive) setDragActive(true);
  }

  function onDragLeave(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragActive(false);
  }

  const dropzoneClasses = `${styles.dropzone} ${dragActive ? styles.dropzoneActive : ""}`;

  return (
    <div
      className={styles.backdrop}
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        aria-describedby={error ? errorId : undefined}
        className={styles.dialog}
      >
        <h2 id={headingId} className={`${styles.dialogHeading} display`}>
          Choose a photo
        </h2>

        <label
          htmlFor={inputId}
          className={dropzoneClasses}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
        >
          <span className={styles.dropzonePrimary}>
            Drop a photo here or click to pick
          </span>
          <span className={styles.dropzoneHint}>
            PNG, JPG, or WEBP · up to 5 MB
          </span>
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

        {error && (
          <p id={errorId} role="alert" className={styles.error}>
            {error.message}
          </p>
        )}

        <div className={styles.dialogActions}>
          <button
            type="button"
            onClick={onClose}
            className={styles.cancelButton}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
