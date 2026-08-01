import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { activePetStorageKey } from "@/lib/activePet";
import { GOAL_BASELINE_DAYS } from "@/lib/tractive.format";
import type { PetRead } from "@/lib/pets";
import { DashboardWithPet } from "./DashboardWithPet";

const { pushMock, fetchRollupsMock, fetchWeightMock } = vi.hoisted(() => ({
  pushMock: vi.fn<(href: string) => void>(),
  fetchRollupsMock: vi.fn(),
  fetchWeightMock: vi.fn(),
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

vi.mock("@/lib/weight", async () => {
  const actual = await vi.importActual<typeof import("@/lib/weight")>("@/lib/weight");
  return {
    ...actual,
    fetchPetWeightSeries: (...args: Parameters<typeof actual.fetchPetWeightSeries>) =>
      fetchWeightMock(...args),
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

const recordLevelVitalFields = {
  heart_rate_record_count: 0,
  heart_rate_record_mean: null,
  heart_rate_ci95_half_width: null,
  respiratory_rate_record_count: 0,
  respiratory_rate_record_mean: null,
  respiratory_rate_ci95_half_width: null,
  respiratory_rate_night_record_count: 0,
  respiratory_rate_night_record_mean: null,
  respiratory_rate_day_record_count: 0,
  respiratory_rate_day_record_mean: null,
  sleep_longest_bout_minutes: 0,
  sleep_bout_count: 0,
  sleep_fragmentation_index: null,
  outings_count: 0,
  outings_total_minutes: 0,
  outings: [],
};

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
  fetchWeightMock.mockReset();
  fetchWeightMock.mockResolvedValue([]);
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
    await waitFor(() => expect(fetchRollupsMock).toHaveBeenCalledWith("pet-2", GOAL_BASELINE_DAYS));
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
    await waitFor(() => expect(fetchRollupsMock).toHaveBeenCalledWith("pet-1", GOAL_BASELINE_DAYS));

    await user.click(screen.getByRole("button", { name: "30d" }));

    await waitFor(() => expect(fetchRollupsMock).toHaveBeenCalledWith("pet-1", 30));
  });

  it("widens a narrow range up to the goal baseline, and never narrows a wide one", async () => {
    const user = userEvent.setup();
    render(
      <DashboardWithPet
        pets={[makePet()]}
        activePetId="pet-1"
        userId={USER_ID}
        todayLabel="Sat, May 23"
      />,
    );

    await waitFor(() => expect(fetchRollupsMock).toHaveBeenCalledWith("pet-1", GOAL_BASELINE_DAYS));

    await user.click(screen.getByRole("button", { name: "90d" }));

    await waitFor(() => expect(fetchRollupsMock).toHaveBeenCalledWith("pet-1", 90));
    expect(fetchRollupsMock).not.toHaveBeenCalledWith("pet-1", 7);
  });

  it("keeps the loaded banner visible while a range switch is refetching", async () => {
    const user = userEvent.setup();
    const loadedRollup = {
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
      ...recordLevelVitalFields,
      gps_distance_km: 3.0,
    };
    fetchRollupsMock.mockResolvedValueOnce({ daily: [loadedRollup] });
    // Leave the range-switch fetch pending so we observe the in-flight state.
    let resolvePending: (value: { daily: (typeof loadedRollup)[] }) => void = () => {};
    fetchRollupsMock.mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePending = resolve;
      }),
    );

    render(
      <DashboardWithPet
        pets={[makePet()]}
        activePetId="pet-1"
        userId={USER_ID}
        todayLabel="Sat, May 23"
      />,
    );
    await waitFor(() => expect(screen.getAllByText(/1h 30m/i).length).toBeGreaterThan(0));

    await user.click(screen.getByRole("button", { name: "30d" }));
    await waitFor(() => expect(fetchRollupsMock).toHaveBeenCalledWith("pet-1", 30));

    // The banner must not flash back to its "not connected" placeholder while
    // the new range is still loading.
    expect(
      screen.queryByRole("heading", { name: /connect tractive to see/i }),
    ).not.toBeInTheDocument();
    expect(screen.getAllByText(/1h 30m/i).length).toBeGreaterThan(0);

    resolvePending({ daily: [loadedRollup] });
  });

  it("fetches and re-fetches the weight series for the active range", async () => {
    const user = userEvent.setup();
    fetchWeightMock.mockResolvedValue([
      { date: "2024-05-20", label: "May 20", weightGrams: 27400 },
      { date: "2024-05-23", label: "May 23", weightGrams: 27600 },
    ]);
    render(
      <DashboardWithPet
        pets={[makePet()]}
        activePetId="pet-1"
        userId={USER_ID}
        todayLabel="Sat, May 23"
      />,
    );
    await waitFor(() => expect(fetchWeightMock).toHaveBeenCalledWith("pet-1", 7));
    // The weight card renders its latest reading (headline + chart callout).
    expect((await screen.findAllByText("27.6 kg")).length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: "90d" }));
    await waitFor(() => expect(fetchWeightMock).toHaveBeenCalledWith("pet-1", 90));
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
          ...recordLevelVitalFields,
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
