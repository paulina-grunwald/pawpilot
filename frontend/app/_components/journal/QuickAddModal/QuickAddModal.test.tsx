import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { JournalEntryRead } from "@/lib/journal.schemas";
import { QuickAddModal } from "./QuickAddModal";

vi.mock("@/lib/journal", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/journal")>();
  return {
    ...actual,
    createJournalEntry: vi.fn(),
    updateJournalEntry: vi.fn(),
  };
});

import { createJournalEntry, updateJournalEntry } from "@/lib/journal";

const createMock = vi.mocked(createJournalEntry);
const updateMock = vi.mocked(updateJournalEntry);

function makeEntry(overrides: Partial<JournalEntryRead> = {}): JournalEntryRead {
  return {
    id: "entry-1",
    pet_id: "pet-1",
    entry_type: "weight",
    payload: { entry_type: "weight", weight_grams: 21400, source: "home_scale" },
    occurred_at: "2026-06-10T08:10:00Z",
    note: null,
    tags: [],
    is_concern: false,
    photo_path: null,
    photo_url: null,
    created_at: "2026-06-10T08:10:05Z",
    updated_at: "2026-06-10T08:10:05Z",
    ...overrides,
  };
}

function renderModal(props: Partial<Parameters<typeof QuickAddModal>[0]> = {}) {
  const onSaved = vi.fn();
  const onClose = vi.fn();
  render(
    <QuickAddModal
      petId="pet-1"
      petName="Luna"
      open
      onClose={onClose}
      onSaved={onSaved}
      {...props}
    />,
  );
  return { onSaved, onClose };
}

beforeEach(() => {
  createMock.mockReset();
  updateMock.mockReset();
});

describe("QuickAddModal type picker", () => {
  it("shows all 8 entry type tiles", () => {
    renderModal();

    for (const label of [
      "Meal",
      "Bathroom",
      "Symptom",
      "Mood",
      "Medication",
      "Weight",
      "Vet visit",
      "Free note",
    ]) {
      expect(screen.getByRole("button", { name: new RegExp(label, "i") })).toBeInTheDocument();
    }
  });

  it("opens the matching form when a tile is picked", async () => {
    const user = userEvent.setup();
    renderModal();

    await user.click(screen.getByRole("button", { name: /Mood/i }));

    expect(screen.getByRole("heading", { name: "Mood" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save mood" })).toBeInTheDocument();
  });

  it("skips the picker when initialEntryType is given", () => {
    renderModal({ initialEntryType: "meal" });

    expect(screen.getByRole("button", { name: "Log this meal" })).toBeInTheDocument();
  });
});

describe("QuickAddModal create", () => {
  it("submits a mood entry with the expected shape", async () => {
    const user = userEvent.setup();
    createMock.mockResolvedValue(makeEntry({ entry_type: "mood" }));
    const { onSaved } = renderModal({ initialEntryType: "mood" });

    await user.click(screen.getByRole("radio", { name: /playful/i }));
    await user.click(screen.getByRole("button", { name: "Save mood" }));

    expect(createMock).toHaveBeenCalledWith(
      "pet-1",
      expect.objectContaining({
        payload: { entry_type: "mood", score: 5 },
        tags: [],
        note: null,
      }),
    );
    expect(onSaved).toHaveBeenCalledWith(expect.anything(), "created");
  });

  it("requires a tag before saving a symptom", async () => {
    const user = userEvent.setup();
    renderModal({ initialEntryType: "symptom" });

    await user.click(screen.getByRole("button", { name: "Save symptom" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Pick at least one symptom tag");
    expect(createMock).not.toHaveBeenCalled();
  });

  it("saves a symptom with tags, severity and body area", async () => {
    const user = userEvent.setup();
    createMock.mockResolvedValue(makeEntry({ entry_type: "symptom" }));
    renderModal({ initialEntryType: "symptom" });

    await user.click(screen.getByRole("button", { name: "scratch" }));
    await user.click(screen.getByRole("radio", { name: /severe/i }));
    await user.click(screen.getByRole("button", { name: "ears" }));
    await user.click(screen.getByRole("button", { name: "Save symptom" }));

    expect(createMock).toHaveBeenCalledWith(
      "pet-1",
      expect.objectContaining({
        payload: { entry_type: "symptom", severity: 5, body_area: "ears" },
        tags: ["scratch"],
      }),
    );
  });

  it("converts weight kilograms to grams", async () => {
    const user = userEvent.setup();
    createMock.mockResolvedValue(makeEntry());
    renderModal({ initialEntryType: "weight" });

    await user.type(screen.getByLabelText("Weight (kg)"), "21.4");
    await user.click(screen.getByRole("button", { name: "Log weight" }));

    expect(createMock).toHaveBeenCalledWith(
      "pet-1",
      expect.objectContaining({
        payload: { entry_type: "weight", weight_grams: 21400, source: "home_scale" },
      }),
    );
  });

  it("applies a recent meal with one tap", async () => {
    const user = userEvent.setup();
    createMock.mockResolvedValue(makeEntry({ entry_type: "meal" }));
    renderModal({
      initialEntryType: "meal",
      recentMeals: [
        {
          entry_type: "meal",
          food_name: "Boiled chicken",
          brand: null,
          amount_grams: 80,
          category: "home_cooked",
        },
      ],
    });

    await user.click(screen.getByRole("button", { name: /Boiled chicken/i }));
    await user.click(screen.getByRole("button", { name: "Log this meal" }));

    expect(createMock).toHaveBeenCalledWith(
      "pet-1",
      expect.objectContaining({
        payload: expect.objectContaining({
          food_name: "Boiled chicken",
          amount_grams: 80,
          category: "home_cooked",
        }),
      }),
    );
  });

  it("hides bristol and color for pee-only bathroom logs", async () => {
    const user = userEvent.setup();
    renderModal({ initialEntryType: "bathroom" });

    expect(screen.getByRole("radiogroup", { name: "Bristol score" })).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "Pee" }));

    expect(screen.queryByRole("radiogroup", { name: "Bristol score" })).not.toBeInTheDocument();
  });

  it("shows a save error when the API rejects", async () => {
    const user = userEvent.setup();
    createMock.mockRejectedValue(new Error("boom"));
    const { onSaved } = renderModal({ initialEntryType: "mood" });

    await user.click(screen.getByRole("button", { name: "Save mood" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't save/i);
    expect(onSaved).not.toHaveBeenCalled();
  });
});

describe("QuickAddModal edit", () => {
  it("prefills from the entry and calls update", async () => {
    const user = userEvent.setup();
    const entry = makeEntry();
    updateMock.mockResolvedValue({
      ...entry,
      payload: { entry_type: "weight", weight_grams: 21000, source: "home_scale" },
    });
    const { onSaved } = renderModal({ entry });

    const weightInput = screen.getByLabelText("Weight (kg)");
    expect(weightInput).toHaveValue(21.4);

    await user.clear(weightInput);
    await user.type(weightInput, "21");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(updateMock).toHaveBeenCalledWith(
      "pet-1",
      "entry-1",
      expect.objectContaining({
        payload: { entry_type: "weight", weight_grams: 21000, source: "home_scale" },
      }),
    );
    expect(onSaved).toHaveBeenCalledWith(expect.anything(), "updated");
  });
});
