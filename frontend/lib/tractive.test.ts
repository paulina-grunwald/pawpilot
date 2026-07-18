import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { getApiBaseUrl } from "./auth";
import {
  TractiveError,
  fetchTractiveRollups,
  uploadTractiveExport,
  type TractiveIngestResult,
  type TractiveRollupsResponse,
} from "./tractive";

const API = getApiBaseUrl();

const sampleResult: TractiveIngestResult = {
  ingest_batch_id: "5ce97a3a-7c2c-4f8e-a0c4-7b21d6e35a5e",
  rollups_upserted: 2,
  raw_payloads_stored: 5,
  date_range_start: "2024-05-15",
  date_range_end: "2024-05-16",
};

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function fakeZip(): File {
  return new File([new Uint8Array([0x50, 0x4b, 0x05, 0x06])], "export.zip", {
    type: "application/zip",
  });
}

describe("TractiveError", () => {
  it("captures code and status", () => {
    const error = new TractiveError("TRACTIVE_INVALID_ZIP", "bad", 400);
    expect(error.code).toBe("TRACTIVE_INVALID_ZIP");
    expect(error.status).toBe(400);
    expect(error.name).toBe("TractiveError");
    expect(error).toBeInstanceOf(Error);
  });
});

describe("uploadTractiveExport", () => {
  it("returns parsed IngestResult on 200", async () => {
    server.use(
      http.post(`${API}/pets/pet-1/tractive/ingest`, () => HttpResponse.json(sampleResult)),
    );
    const result = await uploadTractiveExport("pet-1", fakeZip());
    expect(result.rollups_upserted).toBe(2);
    expect(result.date_range_start).toBe("2024-05-15");
  });

  it("posts the file as multipart with field name 'file'", async () => {
    let receivedFile: { size: number; type: string } | undefined;
    server.use(
      http.post(`${API}/pets/pet-1/tractive/ingest`, async ({ request }) => {
        const form = await request.formData();
        const value = form.get("file") as Blob | null;
        if (value) receivedFile = { size: value.size, type: value.type };
        return HttpResponse.json(sampleResult);
      }),
    );
    await uploadTractiveExport("pet-1", fakeZip());
    expect(receivedFile?.type).toBe("application/zip");
    expect(receivedFile?.size).toBeGreaterThan(0);
  });

  it("throws TRACTIVE_INVALID_ZIP on 400 with matching detail", async () => {
    server.use(
      http.post(`${API}/pets/pet-1/tractive/ingest`, () =>
        HttpResponse.json({ detail: "TRACTIVE_INVALID_ZIP: missing X" }, { status: 400 }),
      ),
    );
    await expect(uploadTractiveExport("pet-1", fakeZip())).rejects.toMatchObject({
      code: "TRACTIVE_INVALID_ZIP",
      status: 400,
    });
  });

  it("throws TRACTIVE_UPLOAD_TOO_LARGE on 413", async () => {
    server.use(
      http.post(`${API}/pets/pet-1/tractive/ingest`, () =>
        HttpResponse.json({ detail: "TRACTIVE_UPLOAD_TOO_LARGE" }, { status: 413 }),
      ),
    );
    await expect(uploadTractiveExport("pet-1", fakeZip())).rejects.toMatchObject({
      code: "TRACTIVE_UPLOAD_TOO_LARGE",
      status: 413,
    });
  });

  it("throws TRACTIVE_PET_NOT_FOUND on 404", async () => {
    server.use(
      http.post(`${API}/pets/pet-1/tractive/ingest`, () =>
        HttpResponse.json({ detail: "PET_NOT_FOUND" }, { status: 404 }),
      ),
    );
    await expect(uploadTractiveExport("pet-1", fakeZip())).rejects.toMatchObject({
      code: "TRACTIVE_PET_NOT_FOUND",
      status: 404,
    });
  });

  it("throws TRACTIVE_UNAUTHENTICATED on 401", async () => {
    server.use(
      http.post(`${API}/pets/pet-1/tractive/ingest`, () => new HttpResponse(null, { status: 401 })),
    );
    await expect(uploadTractiveExport("pet-1", fakeZip())).rejects.toMatchObject({
      code: "TRACTIVE_UNAUTHENTICATED",
      status: 401,
    });
  });

  it("throws NETWORK_ERROR when fetch rejects", async () => {
    server.use(
      http.post(`${API}/pets/pet-1/tractive/ingest`, () => HttpResponse.error()),
    );
    await expect(uploadTractiveExport("pet-1", fakeZip())).rejects.toMatchObject({
      code: "NETWORK_ERROR",
    });
  });
});

const sampleRollupsResponse: TractiveRollupsResponse = {
  daily: [
    {
      date: "2024-05-15",
      minutes_active: 30,
      minutes_low_intensity: 10,
      minutes_moderate: 5,
      minutes_night_sleep: 420,
      minutes_day_sleep: 60,
      minutes_no_signal: 30,
      hourly_minutes_by_category: {},
      heart_rate_mean: 62,
      respiratory_rate_mean: 17,
      heart_rate_record_count: 3,
      heart_rate_record_mean: 62,
      heart_rate_ci95_half_width: 1.5,
      respiratory_rate_record_count: 2,
      respiratory_rate_record_mean: 17,
      respiratory_rate_ci95_half_width: 1.96,
      respiratory_rate_night_record_count: 1,
      respiratory_rate_night_record_mean: 16,
      respiratory_rate_day_record_count: 1,
      respiratory_rate_day_record_mean: 18,
      sleep_longest_bout_minutes: 375,
      sleep_bout_count: 6,
      sleep_fragmentation_index: 4.2,
      outings_count: 1,
      outings_total_minutes: 32,
      outings: [
        {
          started_at: "2024-05-15T07:40:00+00:00",
          ended_at: "2024-05-15T08:12:00+00:00",
          duration_minutes: 32,
          max_distance_meters: 820,
          fix_count: 6,
        },
      ],
      gps_distance_km: 1.2,
    },
  ],
};

describe("fetchTractiveRollups", () => {
  it("returns the parsed list on 200", async () => {
    let receivedUrl: string | undefined;
    server.use(
      http.get(`${API}/pets/pet-1/tractive/rollups`, ({ request }) => {
        receivedUrl = request.url;
        return HttpResponse.json(sampleRollupsResponse);
      }),
    );
    const result = await fetchTractiveRollups("pet-1", 7);
    expect(result.daily).toHaveLength(1);
    expect(result.daily[0].date).toBe("2024-05-15");
    expect(receivedUrl).toContain("days=7");
  });

  it("throws TRACTIVE_PET_NOT_FOUND on 404", async () => {
    server.use(
      http.get(`${API}/pets/pet-1/tractive/rollups`, () =>
        HttpResponse.json({ detail: "PET_NOT_FOUND" }, { status: 404 }),
      ),
    );
    await expect(fetchTractiveRollups("pet-1", 7)).rejects.toMatchObject({
      code: "TRACTIVE_PET_NOT_FOUND",
    });
  });

  it("throws TRACTIVE_UNAUTHENTICATED on 401", async () => {
    server.use(
      http.get(
        `${API}/pets/pet-1/tractive/rollups`,
        () => new HttpResponse(null, { status: 401 }),
      ),
    );
    await expect(fetchTractiveRollups("pet-1", 7)).rejects.toMatchObject({
      code: "TRACTIVE_UNAUTHENTICATED",
    });
  });

  it("throws NETWORK_ERROR when fetch rejects", async () => {
    server.use(
      http.get(`${API}/pets/pet-1/tractive/rollups`, () => HttpResponse.error()),
    );
    await expect(fetchTractiveRollups("pet-1", 7)).rejects.toMatchObject({
      code: "NETWORK_ERROR",
    });
  });
});
