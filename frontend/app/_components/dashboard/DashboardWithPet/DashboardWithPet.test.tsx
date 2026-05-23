import { afterEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { PetRead } from "@/lib/pets";
import { DashboardWithPet, activePetStorageKey } from "./DashboardWithPet";

function makePet(overrides: Partial<PetRead> = {}): PetRead {
  return {
    id: "pet-1",
    name: "Luna",
    breed_other: "Australian Shepherd",
    birthday: "2021-06-14",
    sex: "female",
    spayed_neutered: true,
    weight_grams: 22000,
    notes: null,
    photo_path: null,
    photo_url: null,
    created_at: "2026-05-18T10:13:22Z",
    updated_at: "2026-05-18T10:13:22Z",
    age_years: 4,
    age_months: 11,
    age_weeks: 256,
    life_stage: "adult",
    ...overrides,
  };
}

const USER_ID = "user-uuid";

afterEach(() => {
  window.localStorage.clear();
});

describe("DashboardWithPet", () => {
  it("renders the most-recently-added pet first when no localStorage entry exists", () => {
    const pets = [
      makePet({ id: "pet-1", name: "Luna" }),
      makePet({ id: "pet-2", name: "Bowie", breed_other: "Border Collie" }),
    ];
    render(<DashboardWithPet pets={pets} userId={USER_ID} todayLabel="Sat, May 23" />);
    expect(screen.getByRole("heading", { name: "Luna" })).toBeInTheDocument();
  });

  it("does not render the picker when only one pet exists", () => {
    render(<DashboardWithPet pets={[makePet()]} userId={USER_ID} todayLabel="Sat, May 23" />);
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /pick a dog/i }),
    ).not.toBeInTheDocument();
  });

  it("renders the picker and switches the active pet on selection", async () => {
    const pets = [
      makePet({ id: "pet-1", name: "Luna" }),
      makePet({ id: "pet-2", name: "Bowie", breed_other: "Border Collie" }),
    ];
    const user = userEvent.setup();
    render(<DashboardWithPet pets={pets} userId={USER_ID} todayLabel="Sat, May 23" />);

    const picker = await screen.findByRole("button", { name: /luna/i });
    await user.click(picker);
    await user.click(screen.getByRole("option", { name: /bowie/i }));

    expect(screen.getByRole("heading", { name: "Bowie" })).toBeInTheDocument();
    expect(window.localStorage.getItem(activePetStorageKey(USER_ID))).toBe("pet-2");
  });

  it("restores the active pet from localStorage on render", async () => {
    window.localStorage.setItem(activePetStorageKey(USER_ID), "pet-2");
    const pets = [
      makePet({ id: "pet-1", name: "Luna" }),
      makePet({ id: "pet-2", name: "Bowie", breed_other: "Border Collie" }),
    ];
    render(<DashboardWithPet pets={pets} userId={USER_ID} todayLabel="Sat, May 23" />);
    expect(await screen.findByRole("heading", { name: "Bowie" })).toBeInTheDocument();
  });

  it("falls back to the first pet when localStorage entry is stale", () => {
    window.localStorage.setItem(activePetStorageKey(USER_ID), "pet-deleted");
    const pets = [makePet({ id: "pet-1", name: "Luna" })];
    render(<DashboardWithPet pets={pets} userId={USER_ID} todayLabel="Sat, May 23" />);
    expect(screen.getByRole("heading", { name: "Luna" })).toBeInTheDocument();
  });

  it("renders the Add link pointing at /pets/new when there is exactly one pet", () => {
    render(<DashboardWithPet pets={[makePet()]} userId={USER_ID} todayLabel="Sat, May 23" />);
    const addLink = screen.getByRole("link", { name: /^\+ add$/i });
    expect(addLink).toHaveAttribute("href", "/pets/new");
  });

  it("hides the standalone Add link when more than one pet exists (picker has its own)", async () => {
    const pets = [
      makePet({ id: "pet-1", name: "Luna" }),
      makePet({ id: "pet-2", name: "Bowie", breed_other: "Border Collie" }),
    ];
    render(<DashboardWithPet pets={pets} userId={USER_ID} todayLabel="Sat, May 23" />);

    expect(
      screen.queryByRole("link", { name: /^\+ add$/i }),
    ).not.toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /luna/i }));
    const addAnother = screen.getByRole("link", { name: /\+ add another dog/i });
    expect(addAnother).toHaveAttribute("href", "/pets/new");
  });
});
