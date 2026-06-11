import { getApiBaseUrl } from "./auth";
import type { EntryType } from "./journal.constants";
import type {
  JournalEntryListResponse,
  JournalEntryRead,
  JournalPayload,
} from "./journal.schemas";

export type JournalEntryCreatePayload = {
  payload: JournalPayload;
  occurred_at?: string;
  note?: string | null;
  tags?: string[];
};

export type JournalEntryUpdatePayload = {
  payload?: JournalPayload;
  occurred_at?: string;
  note?: string | null;
  tags?: string[];
};

export type JournalListParams = {
  entryTypes?: EntryType[];
  occurredFrom?: string;
  occurredTo?: string;
  tags?: string[];
  concernsOnly?: boolean;
  search?: string;
  limit?: number;
  cursor?: string;
};

export type JournalErrorCode =
  | "PET_NOT_FOUND"
  | "ENTRY_NOT_FOUND"
  | "ENTRY_TYPE_IMMUTABLE"
  | "JOURNAL_VALIDATION_ERROR"
  | "JOURNAL_UNAUTHENTICATED"
  | "INVALID_CURSOR"
  | "ENTRY_PHOTO_UNSUPPORTED_MEDIA_TYPE"
  | "ENTRY_PHOTO_TOO_LARGE"
  | "UNKNOWN";

export class JournalError extends Error {
  readonly code: JournalErrorCode;
  readonly status?: number;

  constructor(code: JournalErrorCode, message: string, status?: number) {
    super(message);
    this.code = code;
    this.status = status;
    this.name = "JournalError";
  }
}

function journalErrorForStatus(status: number): JournalErrorCode {
  if (status === 400) return "INVALID_CURSOR";
  if (status === 401) return "JOURNAL_UNAUTHENTICATED";
  if (status === 404) return "ENTRY_NOT_FOUND";
  if (status === 409) return "ENTRY_TYPE_IMMUTABLE";
  if (status === 413) return "ENTRY_PHOTO_TOO_LARGE";
  if (status === 415) return "ENTRY_PHOTO_UNSUPPORTED_MEDIA_TYPE";
  if (status === 422) return "JOURNAL_VALIDATION_ERROR";
  return "UNKNOWN";
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new JournalError(
      journalErrorForStatus(response.status),
      `Request failed with ${response.status}`,
      response.status,
    );
  }
  return (await response.json()) as T;
}

export function buildJournalSearchParams(params: JournalListParams): URLSearchParams {
  const searchParams = new URLSearchParams();
  for (const entryType of params.entryTypes ?? []) {
    searchParams.append("entry_type", entryType);
  }
  if (params.occurredFrom) searchParams.set("occurred_from", params.occurredFrom);
  if (params.occurredTo) searchParams.set("occurred_to", params.occurredTo);
  for (const tag of params.tags ?? []) {
    searchParams.append("tag", tag);
  }
  if (params.concernsOnly) searchParams.set("concerns_only", "true");
  if (params.search) searchParams.set("search", params.search);
  if (params.limit !== undefined) searchParams.set("limit", String(params.limit));
  if (params.cursor) searchParams.set("cursor", params.cursor);
  return searchParams;
}

export async function listJournalEntries(
  petId: string,
  params: JournalListParams = {},
): Promise<JournalEntryListResponse> {
  const query = buildJournalSearchParams(params).toString();
  const suffix = query ? `?${query}` : "";
  const response = await fetch(`${getApiBaseUrl()}/pets/${petId}/journal${suffix}`, {
    credentials: "include",
    cache: "no-store",
  });
  return readJson<JournalEntryListResponse>(response);
}

export async function createJournalEntry(
  petId: string,
  payload: JournalEntryCreatePayload,
): Promise<JournalEntryRead> {
  const response = await fetch(`${getApiBaseUrl()}/pets/${petId}/journal`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return readJson<JournalEntryRead>(response);
}

export async function updateJournalEntry(
  petId: string,
  entryId: string,
  payload: JournalEntryUpdatePayload,
): Promise<JournalEntryRead> {
  const response = await fetch(`${getApiBaseUrl()}/pets/${petId}/journal/${entryId}`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return readJson<JournalEntryRead>(response);
}

export async function deleteJournalEntry(petId: string, entryId: string): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/pets/${petId}/journal/${entryId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) {
    throw new JournalError(
      journalErrorForStatus(response.status),
      `DELETE journal entry failed with ${response.status}`,
      response.status,
    );
  }
}

export async function uploadJournalEntryPhoto(
  petId: string,
  entryId: string,
  file: File,
): Promise<JournalEntryRead> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${getApiBaseUrl()}/pets/${petId}/journal/${entryId}/photo`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  return readJson<JournalEntryRead>(response);
}

export async function deleteJournalEntryPhoto(petId: string, entryId: string): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/pets/${petId}/journal/${entryId}/photo`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) {
    throw new JournalError(
      journalErrorForStatus(response.status),
      `DELETE journal photo failed with ${response.status}`,
      response.status,
    );
  }
}
