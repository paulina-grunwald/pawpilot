import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { activePetStorageKey } from "@/lib/activePet";
import type { PetRead } from "@/lib/pets";
import { FloatingDockProvider, useFloatingDock } from "../FloatingDockContext";
import { JournalFab } from "./JournalFab";

const { listPetsMock, pathnameMock } = vi.hoisted(() => ({
  listPetsMock: vi.fn<() => Promise<PetRead[]>>(),
  pathnameMock: vi.fn<() => string>(() => "/dashboard"),
}));

vi.mock("next/navigation", () => ({ usePathname: () => pathnameMock() }));

vi.mock("@/lib/pets", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/pets")>();
  return { ...actual, listPetsForBrowser: listPetsMock };
});

vi.mock("@/lib/journal", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/journal")>();
  return { ...actual, createJournalEntry: vi.fn(), updateJournalEntry: vi.fn() };
});

const USER_ID = "user-uuid";

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

afterEach(() => {
  listPetsMock.mockReset();
  pathnameMock.mockReturnValue("/dashboard");
  window.localStorage.clear();
});

function twoPets(): PetRead[] {
  return [
    makePet({ id: "pet-1", name: "Luna" }),
    makePet({ id: "pet-2", name: "Bowie", breed_other: "Border Collie" }),
  ];
}

describe("JournalFab", () => {
  it("shows the launcher and keeps the menu closed until tapped", () => {
    render(<JournalFab userId={USER_ID} />);
    expect(screen.getByRole("button", { name: /log a journal entry/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /log meal/i })).not.toBeInTheDocument();
    expect(listPetsMock).not.toHaveBeenCalled();
  });

  it("opens the speed-dial and lazily loads the pets on first tap", async () => {
    listPetsMock.mockResolvedValue([makePet()]);
    const user = userEvent.setup();
    render(<JournalFab userId={USER_ID} />);

    await user.click(screen.getByRole("button", { name: /log a journal entry/i }));

    expect(await screen.findByRole("button", { name: /log meal/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /log bathroom/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /log symptom/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /log mood/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /more entry types/i })).toBeInTheDocument();
    expect(listPetsMock).toHaveBeenCalledTimes(1);
  });

  it("opens the quick-add modal pre-selected to the tapped type", async () => {
    listPetsMock.mockResolvedValue([makePet()]);
    const user = userEvent.setup();
    render(<JournalFab userId={USER_ID} />);

    await user.click(screen.getByRole("button", { name: /log a journal entry/i }));
    await user.click(await screen.findByRole("button", { name: /log symptom/i }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save symptom" })).toBeInTheDocument();
  });

  it("opens the full type picker from More…", async () => {
    listPetsMock.mockResolvedValue([makePet()]);
    const user = userEvent.setup();
    render(<JournalFab userId={USER_ID} />);

    await user.click(screen.getByRole("button", { name: /log a journal entry/i }));
    await user.click(await screen.findByRole("button", { name: /more entry types/i }));

    expect(screen.getByRole("heading", { name: "What happened?" })).toBeInTheDocument();
  });

  it("prompts to add a dog when the user has none", async () => {
    listPetsMock.mockResolvedValue([]);
    const user = userEvent.setup();
    render(<JournalFab userId={USER_ID} />);

    await user.click(screen.getByRole("button", { name: /log a journal entry/i }));

    expect(await screen.findByRole("link", { name: /add a dog to start logging/i })).toHaveAttribute(
      "href",
      "/pets/new",
    );
    expect(screen.queryByRole("button", { name: /log meal/i })).not.toBeInTheDocument();
  });

  it("retries loading the pets after a failure", async () => {
    listPetsMock.mockRejectedValueOnce(new Error("down")).mockResolvedValueOnce([makePet()]);
    const user = userEvent.setup();
    render(<JournalFab userId={USER_ID} />);

    await user.click(screen.getByRole("button", { name: /log a journal entry/i }));
    await user.click(await screen.findByRole("button", { name: /try again/i }));

    expect(await screen.findByRole("button", { name: /log meal/i })).toBeInTheDocument();
    expect(listPetsMock).toHaveBeenCalledTimes(2);
  });

  it("logs for the dog named in the route", async () => {
    pathnameMock.mockReturnValue("/dashboard/pet-2");
    listPetsMock.mockResolvedValue(twoPets());
    const user = userEvent.setup();
    render(<JournalFab userId={USER_ID} />);

    await user.click(screen.getByRole("button", { name: /log a journal entry/i }));
    await user.click(await screen.findByRole("button", { name: /log meal/i }));

    // The quick-add modal echoes the pet it will save the entry against.
    expect(screen.getByText("Bowie")).toBeInTheDocument();
  });

  it("falls back to the last-focused dog on a route without a pet", async () => {
    window.localStorage.setItem(activePetStorageKey(USER_ID), "pet-2");
    pathnameMock.mockReturnValue("/chat");
    listPetsMock.mockResolvedValue(twoPets());
    const user = userEvent.setup();
    render(<JournalFab userId={USER_ID} />);

    await user.click(screen.getByRole("button", { name: /log a journal entry/i }));
    await user.click(await screen.findByRole("button", { name: /log meal/i }));

    expect(screen.getByText("Bowie")).toBeInTheDocument();
  });

  it("does not render a pet picker inside the menu", async () => {
    pathnameMock.mockReturnValue("/dashboard/pet-1");
    listPetsMock.mockResolvedValue(twoPets());
    const user = userEvent.setup();
    render(<JournalFab userId={USER_ID} />);

    await user.click(screen.getByRole("button", { name: /log a journal entry/i }));
    await screen.findByRole("button", { name: /log meal/i });

    expect(screen.queryByRole("option")).not.toBeInTheDocument();
  });

  it("hides the launcher while the chat panel is open", async () => {
    const user = userEvent.setup();
    render(
      <FloatingDockProvider>
        <JournalFab userId={USER_ID} />
        <ChatToggle />
      </FloatingDockProvider>,
    );

    expect(screen.getByRole("button", { name: /log a journal entry/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /open chat/i }));

    expect(screen.queryByRole("button", { name: /log a journal entry/i })).not.toBeInTheDocument();
  });
});

function ChatToggle() {
  const { setChatOpen } = useFloatingDock();
  return (
    <button type="button" onClick={() => setChatOpen(true)}>
      open chat
    </button>
  );
}
