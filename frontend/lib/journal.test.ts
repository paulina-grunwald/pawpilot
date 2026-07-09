import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { getApiBaseUrl } from "./auth";
import {
  JournalError,
  buildJournalSearchParams,
  createJournalEntry,
  deleteJournalEntry,
  deleteJournalEntryPhoto,
  listJournalEntries,
  updateJournalEntry,
  uploadJournalEntryPhoto,
} from "./journal";
import type { JournalEntryRead } from "./journal.schemas";

const API = getApiBaseUrl();
const PET_ID = "pet-1";

export const sampleEntry: JournalEntryRead = {
  id: "entry-1",
  pet_id: PET_ID,
  entry_type: "meal",
  payload: {
    entry_type: "meal",
    food_name: "Acana Grain-Free",
    brand: "Acana",
    amount_grams: 100,
    category: "kibble",
  },
  occurred_at: "2026-06-11T08:10:00Z",
  note: null,
  tags: [],
  is_concern: false,
  photo_path: null,
  photo_url: null,
  created_at: "2026-06-11T08:10:05Z",
  updated_at: "2026-06-11T08:10:05Z",
};

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("JournalError", () => {
  it("captures code and status", () => {
    const error = new JournalError("ENTRY_NOT_FOUND", "missing", 404);
    expect(error.code).toBe("ENTRY_NOT_FOUND");
    expect(error.status).toBe(404);
    expect(error.name).toBe("JournalError");
  });
});

describe("buildJournalSearchParams", () => {
  it("returns empty params when nothing is set", () => {
    expect(buildJournalSearchParams({}).toString()).toBe("");
  });

  it("maps every filter to the backend query contract", () => {
    const params = buildJournalSearchParams({
      entryTypes: ["meal", "symptom"],
      occurredFrom: "2026-06-04T00:00:00Z",
      occurredTo: "2026-06-11T00:00:00Z",
      tags: ["ears", "limp"],
      concernsOnly: true,
      search: "kibble",
      limit: 25,
      cursor: "abc",
    });

    expect(params.getAll("entry_type")).toEqual(["meal", "symptom"]);
    expect(params.get("occurred_from")).toBe("2026-06-04T00:00:00Z");
    expect(params.get("occurred_to")).toBe("2026-06-11T00:00:00Z");
    expect(params.getAll("tag")).toEqual(["ears", "limp"]);
    expect(params.get("concerns_only")).toBe("true");
    expect(params.get("search")).toBe("kibble");
    expect(params.get("limit")).toBe("25");
    expect(params.get("cursor")).toBe("abc");
  });

  it("omits concerns_only when false", () => {
    expect(buildJournalSearchParams({ concernsOnly: false }).has("concerns_only")).toBe(false);
  });
});

describe("listJournalEntries", () => {
  it("fetches with filters and returns the page", async () => {
    server.use(
      http.get(`${API}/pets/${PET_ID}/journal`, ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.get("search")).toBe("kibble");
        return HttpResponse.json({
          items: [sampleEntry],
          next_cursor: "cursor-2",
          total_matching: 7,
        });
      }),
    );

    const page = await listJournalEntries(PET_ID, { search: "kibble" });

    expect(page.items).toHaveLength(1);
    expect(page.next_cursor).toBe("cursor-2");
    expect(page.total_matching).toBe(7);
  });

  it("throws INVALID_CURSOR on 400", async () => {
    server.use(
      http.get(`${API}/pets/${PET_ID}/journal`, () =>
        HttpResponse.json({ detail: "INVALID_CURSOR" }, { status: 400 }),
      ),
    );

    await expect(listJournalEntries(PET_ID, { cursor: "junk" })).rejects.toMatchObject({
      code: "INVALID_CURSOR",
    });
  });
});

describe("createJournalEntry", () => {
  it("posts the body and returns the created entry", async () => {
    server.use(
      http.post(`${API}/pets/${PET_ID}/journal`, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        expect(body.payload).toMatchObject({ entry_type: "meal" });
        return HttpResponse.json(sampleEntry, { status: 201 });
      }),
    );

    const created = await createJournalEntry(PET_ID, { payload: sampleEntry.payload });

    expect(created.id).toBe("entry-1");
  });

  it("throws JOURNAL_VALIDATION_ERROR on 422", async () => {
    server.use(
      http.post(`${API}/pets/${PET_ID}/journal`, () =>
        HttpResponse.json({ detail: "bad" }, { status: 422 }),
      ),
    );

    await expect(
      createJournalEntry(PET_ID, { payload: sampleEntry.payload }),
    ).rejects.toMatchObject({ code: "JOURNAL_VALIDATION_ERROR" });
  });
});

describe("updateJournalEntry", () => {
  it("patches and surfaces ENTRY_TYPE_IMMUTABLE on 409", async () => {
    server.use(
      http.patch(`${API}/pets/${PET_ID}/journal/entry-1`, () =>
        HttpResponse.json({ detail: "ENTRY_TYPE_IMMUTABLE" }, { status: 409 }),
      ),
    );

    await expect(
      updateJournalEntry(PET_ID, "entry-1", { payload: sampleEntry.payload }),
    ).rejects.toMatchObject({ code: "ENTRY_TYPE_IMMUTABLE" });
  });
});

describe("deleteJournalEntry", () => {
  it("resolves on 204", async () => {
    server.use(
      http.delete(
        `${API}/pets/${PET_ID}/journal/entry-1`,
        () => new HttpResponse(null, { status: 204 }),
      ),
    );

    await expect(deleteJournalEntry(PET_ID, "entry-1")).resolves.toBeUndefined();
  });

  it("throws ENTRY_NOT_FOUND on 404", async () => {
    server.use(
      http.delete(`${API}/pets/${PET_ID}/journal/entry-1`, () =>
        HttpResponse.json({ detail: "ENTRY_NOT_FOUND" }, { status: 404 }),
      ),
    );

    await expect(deleteJournalEntry(PET_ID, "entry-1")).rejects.toMatchObject({
      code: "ENTRY_NOT_FOUND",
    });
  });
});

describe("journal photo client", () => {
  it("uploads multipart and returns the entry", async () => {
    server.use(
      http.post(`${API}/pets/${PET_ID}/journal/entry-1/photo`, () =>
        HttpResponse.json({ ...sampleEntry, photo_path: "journal/pet-1/x.jpg" }),
      ),
    );

    const file = new File([new Uint8Array([1, 2, 3])], "photo.jpg", { type: "image/jpeg" });
    const updated = await uploadJournalEntryPhoto(PET_ID, "entry-1", file);

    expect(updated.photo_path).toBe("journal/pet-1/x.jpg");
  });

  it("surfaces 415 as unsupported media type", async () => {
    server.use(
      http.post(`${API}/pets/${PET_ID}/journal/entry-1/photo`, () =>
        HttpResponse.json({ detail: "nope" }, { status: 415 }),
      ),
    );

    const file = new File([new Uint8Array([1])], "note.txt", { type: "text/plain" });
    await expect(uploadJournalEntryPhoto(PET_ID, "entry-1", file)).rejects.toMatchObject({
      code: "ENTRY_PHOTO_UNSUPPORTED_MEDIA_TYPE",
    });
  });

  it("detaches photo on 204", async () => {
    server.use(
      http.delete(
        `${API}/pets/${PET_ID}/journal/entry-1/photo`,
        () => new HttpResponse(null, { status: 204 }),
      ),
    );

    await expect(deleteJournalEntryPhoto(PET_ID, "entry-1")).resolves.toBeUndefined();
  });
});
