import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { PetRead } from "@/lib/pets";
import { DashboardWithPet, activePetStorageKey } from "./DashboardWithPet";

const fetchRollupsMock = vi.fn();
vi.mock("@/lib/tractive", async () => {
  const actual = await vi.importActual<typeof import("@/lib/tractive")>("@/lib/tractive");
  return {
    ...actual,
    fetchTractiveRollups: (...args: Parameters<typeof actual.fetchTractiveRollups>) =>
      fetchRollupsMock(...args),
  };
});

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

beforeEach(() => {
  fetchRollupsMock.mockReset();
  fetchRollupsMock.mockResolvedValue({ daily: [] });
});

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

  it("fetches rollups for the active pet on mount", async () => {
    render(<DashboardWithPet pets={[makePet()]} userId={USER_ID} todayLabel="Sat, May 23" />);
    await waitFor(() => expect(fetchRollupsMock).toHaveBeenCalledWith("pet-1", 7));
  });

  it("re-fetches rollups when the active pet changes", async () => {
    const pets = [
      makePet({ id: "pet-1", name: "Luna" }),
      makePet({ id: "pet-2", name: "Bowie", breed_other: "Border Collie" }),
    ];
    const user = userEvent.setup();
    render(<DashboardWithPet pets={pets} userId={USER_ID} todayLabel="Sat, May 23" />);
    await waitFor(() => expect(fetchRollupsMock).toHaveBeenCalledWith("pet-1", 7));

    await user.click(await screen.findByRole("button", { name: /luna/i }));
    await user.click(screen.getByRole("option", { name: /bowie/i }));

    await waitFor(() => expect(fetchRollupsMock).toHaveBeenCalledWith("pet-2", 7));
  });

  it("renders activity ring numbers once rollups arrive", async () => {
    fetchRollupsMock.mockResolvedValue({
      daily: [
        {
          date: "2024-05-15",
          minutes_active: 90,
          minutes_low_intensity: 10,
          minutes_moderate: 5,
          minutes_night_sleep: 420,
          minutes_day_sleep: 60,
          minutes_no_signal: 30,
          hourly_minutes_by_category: {},
          heart_rate_mean: 62,
          respiratory_rate_mean: 17,
          gps_distance_km: 3.0,
        },
      ],
    });
    render(<DashboardWithPet pets={[makePet()]} userId={USER_ID} todayLabel="Sat, May 23" />);
    // The active-minutes value lands in both the ring label and the stat tile.
    await waitFor(() => expect(screen.getAllByText(/1h 30m/i).length).toBeGreaterThan(0));
    expect(
      screen.queryByRole("heading", { name: /connect tractive to see/i }),
    ).not.toBeInTheDocument();
  });

  it("falls back to the placeholder state on a fetch error", async () => {
    fetchRollupsMock.mockRejectedValue(new Error("boom"));
    render(<DashboardWithPet pets={[makePet()]} userId={USER_ID} todayLabel="Sat, May 23" />);
    expect(
      await screen.findByRole("heading", { name: /connect tractive to see/i }),
    ).toBeInTheDocument();
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
