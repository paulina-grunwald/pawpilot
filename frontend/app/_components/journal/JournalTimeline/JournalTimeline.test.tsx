import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { JournalEntryListResponse, JournalEntryRead } from "@/lib/journal.schemas";
import { JournalTimeline } from "./JournalTimeline";

vi.mock("@/lib/journal", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/journal")>();
  return {
    ...actual,
    listJournalEntries: vi.fn(),
    deleteJournalEntry: vi.fn(),
    createJournalEntry: vi.fn(),
    updateJournalEntry: vi.fn(),
  };
});

import { deleteJournalEntry, listJournalEntries } from "@/lib/journal";

const listMock = vi.mocked(listJournalEntries);
const deleteMock = vi.mocked(deleteJournalEntry);

const TODAY = new Date();
const YESTERDAY = new Date(TODAY.getTime() - 24 * 60 * 60 * 1000);

function makeEntry(overrides: Partial<JournalEntryRead> = {}): JournalEntryRead {
  return {
    id: "entry-1",
    pet_id: "pet-1",
    entry_type: "meal",
    payload: {
      entry_type: "meal",
      food_name: "Acana Grain-Free",
      brand: null,
      amount_grams: 100,
      category: "kibble",
    },
    occurred_at: TODAY.toISOString(),
    note: null,
    tags: [],
    is_concern: false,
    photo_path: null,
    photo_url: null,
    created_at: TODAY.toISOString(),
    updated_at: TODAY.toISOString(),
    ...overrides,
  };
}

function makePage(
  items: JournalEntryRead[],
  overrides: Partial<JournalEntryListResponse> = {},
): JournalEntryListResponse {
  return { items, next_cursor: null, total_matching: items.length, ...overrides };
}

function renderTimeline(initialPage: JournalEntryListResponse) {
  return render(<JournalTimeline petId="pet-1" petName="Luna" initialPage={initialPage} />);
}

beforeEach(() => {
  listMock.mockReset();
  deleteMock.mockReset();
});

describe("JournalTimeline feed", () => {
  it("groups entries by day with labels and counts", () => {
    renderTimeline(
      makePage([
        makeEntry({ id: "a" }),
        makeEntry({ id: "b", occurred_at: YESTERDAY.toISOString() }),
      ]),
    );

    expect(screen.getByRole("heading", { name: "Today" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^Yesterday/ })).toBeInTheDocument();
    expect(screen.getByText("2 entries")).toBeInTheDocument();
  });

  it("shows the empty state with three starters when there are no entries", () => {
    renderTimeline(makePage([]));

    expect(screen.getByText("Luna’s journal is empty.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Add your first meal/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Log their mood/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Note a symptom/i })).toBeInTheDocument();
  });

  it("refetches with the search term after the debounce", async () => {
    const user = userEvent.setup();
    listMock.mockResolvedValue(makePage([]));
    renderTimeline(makePage([makeEntry()]));

    await user.type(screen.getByLabelText("Search notes and tags"), "kibble");

    await waitFor(() =>
      expect(listMock).toHaveBeenCalledWith(
        "pet-1",
        expect.objectContaining({ search: "kibble" }),
      ),
    );
  });

  it("deletes an entry after two-tap confirm and shows a toast", async () => {
    const user = userEvent.setup();
    deleteMock.mockResolvedValue(undefined);
    renderTimeline(makePage([makeEntry()]));

    await user.click(screen.getByRole("button", { name: "Delete" }));
    await user.click(screen.getByRole("button", { name: "Confirm delete" }));

    expect(deleteMock).toHaveBeenCalledWith("pet-1", "entry-1");
    await waitFor(() =>
      expect(screen.queryByText("Acana Grain-Free")).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("status")).toHaveTextContent("Entry deleted");
  });

  it("loads older entries with the cursor", async () => {
    const user = userEvent.setup();
    const older = makeEntry({ id: "older", occurred_at: YESTERDAY.toISOString() });
    listMock.mockResolvedValue(makePage([older]));
    renderTimeline(makePage([makeEntry()], { next_cursor: "cursor-1", total_matching: 2 }));

    await user.click(screen.getByRole("button", { name: "Load older entries" }));

    await waitFor(() =>
      expect(listMock).toHaveBeenCalledWith(
        "pet-1",
        expect.objectContaining({ cursor: "cursor-1" }),
      ),
    );
    await waitFor(() => expect(screen.getAllByText("Acana Grain-Free")).toHaveLength(2));
  });

  it("opens the filter sheet and refetches when filters change", async () => {
    const user = userEvent.setup();
    listMock.mockResolvedValue(makePage([]));
    renderTimeline(makePage([makeEntry()]));

    await user.click(screen.getByRole("button", { name: "Filter" }));
    await user.click(screen.getByLabelText(/Concerns only/i));

    await waitFor(() =>
      expect(listMock).toHaveBeenCalledWith(
        "pet-1",
        expect.objectContaining({ concernsOnly: true }),
      ),
    );
  });

  it("opens the quick-add type picker from the FAB", async () => {
    const user = userEvent.setup();
    renderTimeline(makePage([makeEntry()]));

    await user.click(screen.getByRole("button", { name: "+ Log" }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "What happened?" })).toBeInTheDocument();
  });
});
