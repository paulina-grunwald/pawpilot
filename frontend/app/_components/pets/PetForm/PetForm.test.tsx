import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { PetForm } from "./PetForm";
import { getApiBaseUrl } from "@/lib/auth";

const replaceSpy = vi.fn();
const refreshSpy = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceSpy, refresh: refreshSpy }),
}));

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  replaceSpy.mockClear();
  refreshSpy.mockClear();
});
afterAll(() => server.close());

const createdPet = {
  id: "pet-created",
  name: "Luna",
  breed_other: "Aussie mix",
  birthday: "2021-06-14",
  sex: "female",
  spayed_neutered: true,
  weight_grams: 22000,
  notes: "",
  photo_path: null,
  photo_url: null,
  created_at: "2026-05-23T10:00:00Z",
  updated_at: "2026-05-23T10:00:00Z",
  age_years: 4,
  age_months: 11,
  age_weeks: 256,
  life_stage: "adult",
};

describe("PetForm — create mode", () => {
  it("submits the form and redirects to the new pet detail page", async () => {
    let receivedBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${getApiBaseUrl()}/pets`, async ({ request }) => {
        receivedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(createdPet, { status: 201 });
      }),
      http.get(`${getApiBaseUrl()}/breeds`, () => HttpResponse.json([])),
    );
    const user = userEvent.setup();
    render(<PetForm mode="create" />);

    await user.type(screen.getByLabelText(/^name$/i), "Luna");
    await user.type(screen.getByRole("combobox"), "Aussie mix");
    await user.click(screen.getByLabelText(/birthday/i));
    const gridcells = screen.getAllByRole("gridcell");
    const selectableCell = gridcells.find((cell) => {
      const button = cell.querySelector("button");
      return button && !button.hasAttribute("disabled");
    });
    await user.click(selectableCell!.querySelector("button")!);
    const weightInput = screen.getByLabelText(/weight/i);
    await user.clear(weightInput);
    await user.type(weightInput, "22");

    await user.click(screen.getByRole("button", { name: /save pet/i }));

    await waitFor(() => expect(receivedBody).not.toBeNull());
    expect(receivedBody!.name).toBe("Luna");
    expect(receivedBody!.weight_grams).toBe(22000);
    expect(receivedBody!.sex).toBe("female");

    await waitFor(() => expect(replaceSpy).toHaveBeenCalledWith("/pets/pet-created"));
  });

  it("does not create a duplicate pet when retrying after a failed photo upload", async () => {
    let createCalls = 0;
    let patchCalls = 0;
    let photoCalls = 0;
    server.use(
      http.post(`${getApiBaseUrl()}/pets`, () => {
        createCalls += 1;
        return HttpResponse.json(createdPet, { status: 201 });
      }),
      http.patch(`${getApiBaseUrl()}/pets/pet-created`, () => {
        patchCalls += 1;
        return HttpResponse.json(createdPet);
      }),
      http.post(`${getApiBaseUrl()}/pets/pet-created/photo`, () => {
        photoCalls += 1;
        return HttpResponse.json({ detail: "PET_PHOTO_TOO_LARGE" }, { status: 413 });
      }),
      http.get(`${getApiBaseUrl()}/breeds`, () => HttpResponse.json([])),
    );
    const user = userEvent.setup();
    render(<PetForm mode="create" />);

    await user.type(screen.getByLabelText(/^name$/i), "Luna");
    await user.click(screen.getByLabelText(/birthday/i));
    const cells = screen.getAllByRole("gridcell");
    const cell = cells.find((c) => {
      const btn = c.querySelector("button");
      return btn && !btn.hasAttribute("disabled");
    });
    await user.click(cell!.querySelector("button")!);
    const weightInput = screen.getByLabelText(/weight/i);
    await user.clear(weightInput);
    await user.type(weightInput, "22");

    await user.click(screen.getByRole("button", { name: /add photo/i }));
    const fileInput = screen.getByLabelText(/pet photo/i) as HTMLInputElement;
    const photoFile = new File([new Uint8Array([0xff, 0xd8, 0xff, 0xe0])], "p.jpg", {
      type: "image/jpeg",
    });
    await user.upload(fileInput, photoFile);

    await user.click(screen.getByRole("button", { name: /save pet/i }));

    await waitFor(() => expect(photoCalls).toBe(1));
    expect(createCalls).toBe(1);
    expect(replaceSpy).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /save pet/i }));

    await waitFor(() => expect(patchCalls).toBe(1));
    expect(createCalls).toBe(1);
    await waitFor(() => expect(replaceSpy).toHaveBeenCalledWith("/pets/pet-created"));
  });

  it("surfaces a friendly error on 422 validation failure", async () => {
    server.use(
      http.post(`${getApiBaseUrl()}/pets`, () =>
        HttpResponse.json({ detail: "invalid" }, { status: 422 }),
      ),
      http.get(`${getApiBaseUrl()}/breeds`, () => HttpResponse.json([])),
    );
    const user = userEvent.setup();
    render(<PetForm mode="create" />);

    await user.type(screen.getByLabelText(/^name$/i), "Luna");
    await user.click(screen.getByLabelText(/birthday/i));
    const cells = screen.getAllByRole("gridcell");
    const cell = cells.find((c) => {
      const btn = c.querySelector("button");
      return btn && !btn.hasAttribute("disabled");
    });
    await user.click(cell!.querySelector("button")!);
    await user.click(screen.getByRole("button", { name: /save pet/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/didn't validate/i));
    expect(replaceSpy).not.toHaveBeenCalled();
  });

  it("shows the required-field error for an empty name", async () => {
    server.use(http.get(`${getApiBaseUrl()}/breeds`, () => HttpResponse.json([])));
    const user = userEvent.setup();
    render(<PetForm mode="create" />);

    await user.click(screen.getByLabelText(/birthday/i));
    const cells = screen.getAllByRole("gridcell");
    const cell = cells.find((c) => {
      const btn = c.querySelector("button");
      return btn && !btn.hasAttribute("disabled");
    });
    await user.click(cell!.querySelector("button")!);
    await user.click(screen.getByRole("button", { name: /save pet/i }));

    await waitFor(() => expect(screen.getByText(/name is required/i)).toBeInTheDocument());
    expect(replaceSpy).not.toHaveBeenCalled();
  });
});

describe("PetForm — edit mode", () => {
  const initialValues = {
    name: "Luna",
    breedOther: "Aussie mix",
    birthday: "2021-06-14",
    sex: "female" as const,
    spayedNeutered: true,
    weightKg: 22,
    notes: "Loves frisbee.",
  };

  it("pre-fills the form from initialValues", () => {
    render(<PetForm mode="edit" petId="pet-1" initialValues={initialValues} />);
    expect(screen.getByLabelText(/^name$/i)).toHaveValue("Luna");
    expect(screen.getByRole("combobox")).toHaveValue("Aussie mix");
    expect(screen.getByLabelText(/notes/i)).toHaveValue("Loves frisbee.");
  });

  it("sends a PATCH to /pets/{id} and redirects to the detail page", async () => {
    let receivedBody: Record<string, unknown> | null = null;
    server.use(
      http.patch(`${getApiBaseUrl()}/pets/pet-1`, async ({ request }) => {
        receivedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ ...createdPet, id: "pet-1" });
      }),
      http.get(`${getApiBaseUrl()}/breeds`, () => HttpResponse.json([])),
    );
    const user = userEvent.setup();
    render(<PetForm mode="edit" petId="pet-1" initialValues={initialValues} />);

    const weight = screen.getByLabelText(/weight/i);
    await user.clear(weight);
    await user.type(weight, "23.5");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => expect(receivedBody).not.toBeNull());
    expect(receivedBody!.weight_grams).toBe(23500);
    await waitFor(() => expect(replaceSpy).toHaveBeenCalledWith("/pets/pet-1"));
  });
});
