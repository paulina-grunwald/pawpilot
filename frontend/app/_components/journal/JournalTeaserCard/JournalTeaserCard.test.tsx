import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { JournalEntryRead } from "@/lib/journal.schemas";
import { JournalTeaserCard } from "./JournalTeaserCard";

function makeEntry(id: string): JournalEntryRead {
  return {
    id,
    pet_id: "pet-1",
    entry_type: "mood",
    payload: { entry_type: "mood", score: 5 },
    occurred_at: "2026-06-11T09:15:00Z",
    note: null,
    tags: [],
    is_concern: false,
    photo_path: null,
    photo_url: null,
    created_at: "2026-06-11T09:15:05Z",
    updated_at: "2026-06-11T09:15:05Z",
  };
}

describe("JournalTeaserCard", () => {
  it("shows an inviting empty state", () => {
    render(<JournalTeaserCard petId="pet-1" petName="Luna" entries={[]} />);

    expect(screen.getByText(/No entries yet/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open Luna’s journal/ })).toHaveAttribute(
      "href",
      "/pets/pet-1/journal",
    );
  });

  it("shows a degraded state with the journal link when entries failed to load", () => {
    render(<JournalTeaserCard petId="pet-1" petName="Luna" entries={null} />);

    expect(screen.getByText(/Couldn’t load recent entries/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open Luna’s journal/ })).toHaveAttribute(
      "href",
      "/pets/pet-1/journal",
    );
  });

  it("renders at most three recent entries", () => {
    render(
      <JournalTeaserCard
        petId="pet-1"
        petName="Luna"
        entries={[makeEntry("a"), makeEntry("b"), makeEntry("c"), makeEntry("d")]}
      />,
    );

    expect(screen.getAllByText("playful · 5/5")).toHaveLength(3);
  });
});
