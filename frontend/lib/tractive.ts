import { getApiBaseUrl } from "./auth";

export type TractiveIngestResult = {
  ingest_batch_id: string;
  rollups_upserted: number;
  raw_payloads_stored: number;
  date_range_start: string | null;
  date_range_end: string | null;
};

export type TractiveErrorCode =
  | "TRACTIVE_INVALID_ZIP"
  | "TRACTIVE_UPLOAD_TOO_LARGE"
  | "TRACTIVE_UNAUTHENTICATED"
  | "TRACTIVE_PET_NOT_FOUND"
  | "NETWORK_ERROR"
  | "UNKNOWN";

export class TractiveError extends Error {
  readonly code: TractiveErrorCode;
  readonly status?: number;

  constructor(code: TractiveErrorCode, message: string, status?: number) {
    super(message);
    this.code = code;
    this.status = status;
    this.name = "TractiveError";
  }
}

function tractiveErrorForStatus(status: number, detail?: string): TractiveErrorCode {
  if (status === 401) return "TRACTIVE_UNAUTHENTICATED";
  if (status === 404) return "TRACTIVE_PET_NOT_FOUND";
  if (status === 413) return "TRACTIVE_UPLOAD_TOO_LARGE";
  if (status === 400 && detail?.startsWith("TRACTIVE_INVALID_ZIP")) return "TRACTIVE_INVALID_ZIP";
  return "UNKNOWN";
}

export async function uploadTractiveExport(
  petId: string,
  file: File,
): Promise<TractiveIngestResult> {
  const formData = new FormData();
  formData.append("file", file);

  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}/pets/${petId}/tractive/ingest`, {
      method: "POST",
      credentials: "include",
      body: formData,
    });
  } catch (error) {
    throw new TractiveError(
      "NETWORK_ERROR",
      error instanceof Error ? error.message : "network error",
    );
  }

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail;
    } catch {
      // Body wasn't JSON; fall through with no detail.
    }
    throw new TractiveError(
      tractiveErrorForStatus(response.status, detail),
      detail ?? `Upload failed with ${response.status}`,
      response.status,
    );
  }

  return (await response.json()) as TractiveIngestResult;
}

export type TractiveDailySummary = {
  date: string;
  minutes_active: number;
  minutes_low_intensity: number;
  minutes_moderate: number;
  minutes_night_sleep: number;
  minutes_day_sleep: number;
  minutes_no_signal: number;
  /** Local-hour-bucketed minutes per category. Keys are stringified hour 0..23. */
  hourly_minutes_by_category: Record<string, Record<string, number>>;
  heart_rate_mean: number | null;
  respiratory_rate_mean: number | null;
  /**
   * Record-level daily vitals: one measurement event counts once and motion
   * contaminated bursts are rejected server-side, so these are safe to chart.
   */
  heart_rate_record_count: number;
  heart_rate_record_mean: number | null;
  heart_rate_ci95_half_width: number | null;
  respiratory_rate_record_count: number;
  respiratory_rate_record_mean: number | null;
  respiratory_rate_ci95_half_width: number | null;
  respiratory_rate_night_record_count: number;
  respiratory_rate_night_record_mean: number | null;
  respiratory_rate_day_record_count: number;
  respiratory_rate_day_record_mean: number | null;
  /**
   * Sleep continuity from the activity timeline: consolidated rest bouts,
   * never clinical sleep stages.
   */
  sleep_longest_bout_minutes: number;
  sleep_bout_count: number;
  sleep_fragmentation_index: number | null;
  /**
   * GPS-detected outings against a data-derived home. Counts and durations
   * are floors: sampling gaps and collar-off time can hide whole outings.
   */
  outings_count: number;
  outings_total_minutes: number;
  outings: TractiveOuting[];
  gps_distance_km: number;
};

export type TractiveOuting = {
  started_at: string;
  ended_at: string;
  duration_minutes: number;
  max_distance_meters: number;
  fix_count: number;
};

export type TractiveRollupsResponse = {
  daily: TractiveDailySummary[];
};

export async function fetchTractiveRollups(
  petId: string,
  days: number,
): Promise<TractiveRollupsResponse> {
  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}/pets/${petId}/tractive/rollups?days=${days}`, {
      credentials: "include",
      cache: "no-store",
    });
  } catch (error) {
    throw new TractiveError(
      "NETWORK_ERROR",
      error instanceof Error ? error.message : "network error",
    );
  }

  if (!response.ok) {
    throw new TractiveError(
      tractiveErrorForStatus(response.status),
      `Request failed with ${response.status}`,
      response.status,
    );
  }

  return (await response.json()) as TractiveRollupsResponse;
}
