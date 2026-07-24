import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { JournalEntryRead } from "@/lib/journal.schemas";
import { EntryCard } from "./EntryCard";

function makeEntry(overrides: Partial<JournalEntryRead> = {}): JournalEntryRead {
  return {
    id: "entry-1",
    pet_id: "pet-1",
    entry_type: "meal",
    payload: {
      entry_type: "meal",
      food_name: "Acana Grain-Free",
      brand: "Acana",
      amount_grams: 100,
      category: "kibble",
    },
    occurred_at: "2026-06-11T08:10:00Z",
    note: null,
    tags: [],
    is_concern: false,
    photo_path: null,
    photo_url: null,
    created_at: "2026-06-11T08:10:05Z",
    updated_at: "2026-06-11T08:10:05Z",
    ...overrides,
  };
}

describe("EntryCard", () => {
  it("renders the meal presentation", () => {
    render(<EntryCard entry={makeEntry()} />);

    expect(screen.getByText("Acana Grain-Free")).toBeInTheDocument();
    expect(screen.getByText("Kibble · Acana")).toBeInTheDocument();
    expect(screen.getByText("100 g")).toBeInTheDocument();
    expect(screen.getByText("Meal")).toBeInTheDocument();
  });

  it("marks concern entries with the concern style", () => {
    const { container } = render(
      <EntryCard
        entry={makeEntry({
          entry_type: "symptom",
          is_concern: true,
          tags: ["scratch"],
          payload: { entry_type: "symptom", severity: 3, body_area: "ears" },
        })}
      />,
    );

    expect(container.firstElementChild?.className).toMatch(/concern/);
  });

  it("shows a Needs attention pill for concern entries", () => {
    render(
      <EntryCard
        entry={makeEntry({
          entry_type: "symptom",
          is_concern: true,
          tags: ["scratch"],
          payload: { entry_type: "symptom", severity: 3, body_area: "ears" },
        })}
      />,
    );

    expect(screen.getByText("Needs attention")).toBeInTheDocument();
  });

  it("does not show the Needs attention pill for non-concern entries", () => {
    render(<EntryCard entry={makeEntry({ is_concern: false })} />);

    expect(screen.queryByText("Needs attention")).not.toBeInTheDocument();
  });

  it("renders the note and non-symptom tags", () => {
    render(<EntryCard entry={makeEntry({ note: "Ate fast", tags: ["good-appetite"] })} />);

    expect(screen.getByText("Ate fast")).toBeInTheDocument();
    expect(screen.getByText("good-appetite")).toBeInTheDocument();
  });

  it("calls onEdit with the entry", async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();
    const entry = makeEntry();
    render(<EntryCard entry={entry} onEdit={onEdit} />);

    await user.click(screen.getByRole("button", { name: "Edit" }));

    expect(onEdit).toHaveBeenCalledWith(entry);
  });

  it("requires a second tap to confirm delete", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    const entry = makeEntry();
    render(<EntryCard entry={entry} onDelete={onDelete} />);

    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(onDelete).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Confirm delete" }));
    expect(onDelete).toHaveBeenCalledWith(entry);
  });
});
