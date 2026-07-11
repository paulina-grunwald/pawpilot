import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { activePetStorageKey } from "@/lib/activePet";
import type { PetRead } from "@/lib/pets";
import { DashboardWithPet } from "./DashboardWithPet";

const { pushMock, fetchRollupsMock } = vi.hoisted(() => ({
  pushMock: vi.fn<(href: string) => void>(),
  fetchRollupsMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: pushMock, prefetch: vi.fn() }),
  usePathname: () => "/dashboard/pet-1",
}));

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

function twoPets(): PetRead[] {
  return [
    makePet({ id: "pet-1", name: "Luna" }),
    makePet({ id: "pet-2", name: "Bowie", breed_other: "Border Collie" }),
  ];
}

beforeEach(() => {
  pushMock.mockReset();
  fetchRollupsMock.mockReset();
  fetchRollupsMock.mockResolvedValue({ daily: [] });
});

afterEach(() => {
  window.localStorage.clear();
});

describe("DashboardWithPet", () => {
  it("renders the pet named by the active id", () => {
    render(
      <DashboardWithPet
        pets={twoPets()}
        activePetId="pet-2"
        userId={USER_ID}
        todayLabel="Sat, May 23"
      />,
    );
    expect(screen.getByRole("heading", { name: "Bowie" })).toBeInTheDocument();
  });

  it("falls back to the first pet when the active id is unknown", () => {
    render(
      <DashboardWithPet
        pets={twoPets()}
        activePetId="pet-gone"
        userId={USER_ID}
        todayLabel="Sat, May 23"
      />,
    );
    expect(screen.getByRole("heading", { name: "Luna" })).toBeInTheDocument();
  });

  it("persists the active pet to localStorage", () => {
    render(
      <DashboardWithPet
        pets={twoPets()}
        activePetId="pet-2"
        userId={USER_ID}
        todayLabel="Sat, May 23"
      />,
    );
    expect(window.localStorage.getItem(activePetStorageKey(USER_ID))).toBe("pet-2");
  });

  it("navigates to the picked pet's dashboard and remembers it", async () => {
    const user = userEvent.setup();
    render(
      <DashboardWithPet
        pets={twoPets()}
        activePetId="pet-1"
        userId={USER_ID}
        todayLabel="Sat, May 23"
      />,
    );

    await user.click(await screen.findByRole("button", { name: /luna/i }));
    await user.click(screen.getByRole("option", { name: /bowie/i }));

    expect(pushMock).toHaveBeenCalledWith("/dashboard/pet-2");
    expect(window.localStorage.getItem(activePetStorageKey(USER_ID))).toBe("pet-2");
  });

  it("does not render the picker when only one pet exists", () => {
    render(
      <DashboardWithPet
        pets={[makePet()]}
        activePetId="pet-1"
        userId={USER_ID}
        todayLabel="Sat, May 23"
      />,
    );
    expect(screen.queryByRole("option")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^\+ add$/i })).toHaveAttribute("href", "/pets/new");
  });

  it("fetches rollups for the active pet on mount", async () => {
    render(
      <DashboardWithPet
        pets={twoPets()}
        activePetId="pet-2"
        userId={USER_ID}
        todayLabel="Sat, May 23"
      />,
    );
    await waitFor(() => expect(fetchRollupsMock).toHaveBeenCalledWith("pet-2", 7));
  });

  it("re-fetches rollups when the range changes", async () => {
    const user = userEvent.setup();
    render(
      <DashboardWithPet
        pets={[makePet()]}
        activePetId="pet-1"
        userId={USER_ID}
        todayLabel="Sat, May 23"
      />,
    );
    await waitFor(() => expect(fetchRollupsMock).toHaveBeenCalledWith("pet-1", 7));

    await user.click(screen.getByRole("button", { name: "30d" }));

    await waitFor(() => expect(fetchRollupsMock).toHaveBeenCalledWith("pet-1", 30));
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
    render(
      <DashboardWithPet
        pets={[makePet()]}
        activePetId="pet-1"
        userId={USER_ID}
        todayLabel="Sat, May 23"
      />,
    );
    await waitFor(() => expect(screen.getAllByText(/1h 30m/i).length).toBeGreaterThan(0));
    expect(
      screen.queryByRole("heading", { name: /connect tractive to see/i }),
    ).not.toBeInTheDocument();
  });

  it("falls back to the placeholder state on a fetch error", async () => {
    fetchRollupsMock.mockRejectedValue(new Error("boom"));
    render(
      <DashboardWithPet
        pets={[makePet()]}
        activePetId="pet-1"
        userId={USER_ID}
        todayLabel="Sat, May 23"
      />,
    );
    expect(
      await screen.findByRole("heading", { name: /connect tractive to see/i }),
    ).toBeInTheDocument();
  });
});
