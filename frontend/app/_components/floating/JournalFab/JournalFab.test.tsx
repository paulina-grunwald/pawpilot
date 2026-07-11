import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { PetRead } from "@/lib/pets";
import { FloatingDockProvider, useFloatingDock } from "../FloatingDockContext";
import { JournalFab, activePetStorageKey } from "./JournalFab";

const { listPetsMock } = vi.hoisted(() => ({
  listPetsMock: vi.fn<() => Promise<PetRead[]>>(),
}));

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
  window.localStorage.clear();
});

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

  it("targets the stored active pet and switches when picked", async () => {
    window.localStorage.setItem(activePetStorageKey(USER_ID), "pet-2");
    listPetsMock.mockResolvedValue([
      makePet({ id: "pet-1", name: "Luna" }),
      makePet({ id: "pet-2", name: "Bowie", breed_other: "Border Collie" }),
    ]);
    const user = userEvent.setup();
    render(<JournalFab userId={USER_ID} />);

    await user.click(screen.getByRole("button", { name: /log a journal entry/i }));

    const picker = await screen.findByRole("button", { name: /bowie/i });
    await user.click(picker);
    await user.click(screen.getByRole("option", { name: /luna/i }));

    expect(window.localStorage.getItem(activePetStorageKey(USER_ID))).toBe("pet-1");
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
