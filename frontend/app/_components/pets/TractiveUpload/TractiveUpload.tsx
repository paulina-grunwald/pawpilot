"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { TractiveError, type TractiveIngestResult, uploadTractiveExport } from "@/lib/tractive";
import styles from "./TractiveUpload.module.css";

type TractiveUploadProps = {
  petId: string;
};

type UploadStatus =
  | { kind: "idle" }
  | { kind: "uploading" }
  | { kind: "success"; result: TractiveIngestResult }
  | { kind: "error"; message: string };

const ERROR_COPY: Record<string, string> = {
  TRACTIVE_INVALID_ZIP: "That doesn't look like a Tractive GDPR export — some files are missing.",
  TRACTIVE_UPLOAD_TOO_LARGE: "The upload is too large. Try a shorter date range.",
  TRACTIVE_PET_NOT_FOUND: "This pet no longer exists.",
  TRACTIVE_UNAUTHENTICATED: "Please sign in again before uploading.",
  NETWORK_ERROR: "We couldn't reach the server. Check your connection and try again.",
};

export function TractiveUpload({ petId }: TractiveUploadProps) {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState<UploadStatus>({ kind: "idle" });

  function resetForAnotherUpload() {
    setSelectedFile(null);
    setStatus({ kind: "idle" });
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleUpload() {
    if (!selectedFile) return;
    setStatus({ kind: "uploading" });
    try {
      const result = await uploadTractiveExport(petId, selectedFile);
      setStatus({ kind: "success", result });
      router.refresh();
    } catch (caught) {
      const code = caught instanceof TractiveError ? caught.code : "UNKNOWN";
      setStatus({
        kind: "error",
        message: ERROR_COPY[code] ?? "Something went wrong while uploading. Try again in a moment.",
      });
    }
  }

  if (status.kind === "success") {
    const { result } = status;
    return (
      <div className={styles.root}>
        <p className={styles.successHeadline}>
          Imported {result.rollups_upserted} {result.rollups_upserted === 1 ? "day" : "days"}
          {result.date_range_start && result.date_range_end
            ? ` (${result.date_range_start} – ${result.date_range_end})`
            : ""}
          .
        </p>
        <button type="button" className={styles.linkButton} onClick={resetForAnotherUpload}>
          Upload another export
        </button>
      </div>
    );
  }

  const isUploading = status.kind === "uploading";

  return (
    <div className={styles.root}>
      <p className={styles.helper}>
        Upload your Tractive GDPR-export <code>.zip</code> to import activity, sleep, vitals, and
        walks.
      </p>
      <input
        ref={fileInputRef}
        type="file"
        accept=".zip,application/zip"
        className={styles.fileInput}
        onChange={(event) => {
          const file = event.target.files?.[0] ?? null;
          setSelectedFile(file);
          if (status.kind === "error") setStatus({ kind: "idle" });
        }}
        disabled={isUploading}
        aria-label="Tractive export zip"
      />
      <button
        type="button"
        onClick={handleUpload}
        disabled={!selectedFile || isUploading}
        className={styles.uploadButton}
      >
        {isUploading ? "Uploading…" : "Upload export"}
      </button>
      {status.kind === "error" && (
        <p role="alert" className={styles.error}>
          {status.message}
        </p>
      )}
    </div>
  );
}
