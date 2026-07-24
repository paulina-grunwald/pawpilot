import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { getApiBaseUrl } from "./auth";
import {
  PetsError,
  createPet,
  deletePet,
  deletePetPhoto,
  listPetsForBrowser,
  toPetPickerOption,
  updatePet,
  uploadPetPhoto,
  type PetRead,
} from "./pets";

const API = getApiBaseUrl();

const samplePet: PetRead = {
  id: "pet-1",
  name: "Luna",
  breed_other: "Aussie mix",
  birthday: "2021-06-14",
  sex: "female",
  spayed_neutered: true,
  weight_grams: 22000,
  notes: null,
  photo_path: null,
  photo_url: null,
  created_at: "2026-05-23T00:00:00Z",
  updated_at: "2026-05-23T00:00:00Z",
  age_years: 4,
  age_months: 11,
  age_weeks: 256,
  life_stage: "adult",
};

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("toPetPickerOption", () => {
  it("maps a PetRead to the id/name/breed picker shape", () => {
    expect(toPetPickerOption(samplePet)).toEqual({
      id: "pet-1",
      name: "Luna",
      breed: "Aussie mix",
    });
  });

  it("falls back to 'Dog' when breed_other is null", () => {
    expect(toPetPickerOption({ ...samplePet, breed_other: null })).toEqual({
      id: "pet-1",
      name: "Luna",
      breed: "Dog",
    });
  });
});

describe("PetsError", () => {
  it("captures code and status", () => {
    const error = new PetsError("PET_NOT_FOUND", "missing", 404);
    expect(error.code).toBe("PET_NOT_FOUND");
    expect(error.status).toBe(404);
    expect(error.name).toBe("PetsError");
    expect(error).toBeInstanceOf(Error);
  });
});

describe("listPetsForBrowser", () => {
  it("returns parsed array on 200", async () => {
    server.use(http.get(`${API}/pets`, () => HttpResponse.json([samplePet])));
    const pets = await listPetsForBrowser();
    expect(pets).toHaveLength(1);
    expect(pets[0].id).toBe("pet-1");
  });

  it("throws PetsError with PET_UNAUTHENTICATED on 401", async () => {
    server.use(http.get(`${API}/pets`, () => new HttpResponse(null, { status: 401 })));
    await expect(listPetsForBrowser()).rejects.toMatchObject({
      code: "PET_UNAUTHENTICATED",
      status: 401,
    });
  });

  it("maps 500 to UNKNOWN", async () => {
    server.use(http.get(`${API}/pets`, () => new HttpResponse(null, { status: 500 })));
    await expect(listPetsForBrowser()).rejects.toMatchObject({
      code: "UNKNOWN",
      status: 500,
    });
  });
});

describe("createPet", () => {
  it("returns the created pet on 201", async () => {
    server.use(http.post(`${API}/pets`, () => HttpResponse.json(samplePet, { status: 201 })));
    const result = await createPet({
      name: "Luna",
      birthday: "2021-06-14",
      sex: "female",
      spayed_neutered: true,
      weight_grams: 22000,
    });
    expect(result.id).toBe("pet-1");
  });

  it("maps 422 to PET_VALIDATION_ERROR", async () => {
    server.use(http.post(`${API}/pets`, () => new HttpResponse(null, { status: 422 })));
    await expect(
      createPet({
        name: "",
        birthday: "2021-06-14",
        sex: "female",
        spayed_neutered: true,
        weight_grams: 22000,
      }),
    ).rejects.toMatchObject({ code: "PET_VALIDATION_ERROR" });
  });
});

describe("updatePet", () => {
  it("returns the updated pet on 200", async () => {
    server.use(
      http.patch(`${API}/pets/pet-1`, () => HttpResponse.json({ ...samplePet, name: "Lunita" })),
    );
    const result = await updatePet("pet-1", { name: "Lunita" });
    expect(result.name).toBe("Lunita");
  });

  it("maps 404 to PET_NOT_FOUND", async () => {
    server.use(http.patch(`${API}/pets/pet-1`, () => new HttpResponse(null, { status: 404 })));
    await expect(updatePet("pet-1", { name: "X" })).rejects.toMatchObject({
      code: "PET_NOT_FOUND",
    });
  });
});

describe("deletePet", () => {
  it("resolves on 204", async () => {
    server.use(http.delete(`${API}/pets/pet-1`, () => new HttpResponse(null, { status: 204 })));
    await expect(deletePet("pet-1")).resolves.toBeUndefined();
  });

  it("throws PetsError on 404", async () => {
    server.use(http.delete(`${API}/pets/pet-1`, () => new HttpResponse(null, { status: 404 })));
    await expect(deletePet("pet-1")).rejects.toMatchObject({ code: "PET_NOT_FOUND" });
  });
});

describe("uploadPetPhoto", () => {
  it("returns pet on 200", async () => {
    server.use(
      http.post(`${API}/pets/pet-1/photo`, () =>
        HttpResponse.json({ ...samplePet, photo_url: "https://media/luna.jpg" }),
      ),
    );
    const file = new File(["abc"], "luna.jpg", { type: "image/jpeg" });
    const result = await uploadPetPhoto("pet-1", file);
    expect(result.photo_url).toBe("https://media/luna.jpg");
  });

  it("maps 413 to PET_PHOTO_TOO_LARGE", async () => {
    server.use(http.post(`${API}/pets/pet-1/photo`, () => new HttpResponse(null, { status: 413 })));
    const file = new File(["x"], "big.jpg", { type: "image/jpeg" });
    await expect(uploadPetPhoto("pet-1", file)).rejects.toMatchObject({
      code: "PET_PHOTO_TOO_LARGE",
    });
  });

  it("maps 415 to PET_PHOTO_UNSUPPORTED_MEDIA_TYPE", async () => {
    server.use(http.post(`${API}/pets/pet-1/photo`, () => new HttpResponse(null, { status: 415 })));
    const file = new File(["x"], "x.heic", { type: "image/heic" });
    await expect(uploadPetPhoto("pet-1", file)).rejects.toMatchObject({
      code: "PET_PHOTO_UNSUPPORTED_MEDIA_TYPE",
    });
  });
});

describe("deletePetPhoto", () => {
  it("returns pet on 200", async () => {
    server.use(http.delete(`${API}/pets/pet-1/photo`, () => HttpResponse.json(samplePet)));
    const result = await deletePetPhoto("pet-1");
    expect(result.id).toBe("pet-1");
  });
});
