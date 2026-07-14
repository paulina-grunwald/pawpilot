import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { JournalEntryRead, JournalPayload } from "@/lib/journal.schemas";
import { JournalStats } from "./JournalStats";

function makeEntry(
  payload: JournalPayload,
  overrides: Partial<JournalEntryRead> = {},
): JournalEntryRead {
  const occurredAt = overrides.occurred_at ?? new Date().toISOString();
  return {
    id: "entry-1",
    pet_id: "pet-1",
    entry_type: payload.entry_type,
    payload,
    occurred_at: occurredAt,
    note: null,
    tags: [],
    is_concern: false,
    photo_path: null,
    photo_url: null,
    created_at: occurredAt,
    updated_at: occurredAt,
    ...overrides,
  };
}

describe("JournalStats", () => {
  it("renders all four stat labels", () => {
    render(<JournalStats entries={[]} />);
    expect(screen.getByText("Current weight")).toBeInTheDocument();
    expect(screen.getByText("Last meal")).toBeInTheDocument();
    expect(screen.getByText("Active med")).toBeInTheDocument();
    expect(screen.getByText("Needs attention")).toBeInTheDocument();
  });

  it("shows the latest weight value with a sparkline", () => {
    const { container } = render(
      <JournalStats
        entries={[
          makeEntry({ entry_type: "weight", weight_grams: 28000, source: "vet" }),
          makeEntry({ entry_type: "weight", weight_grams: 28600, source: "home_scale" }),
        ]}
      />,
    );
    expect(screen.getByText("28.0")).toBeInTheDocument();
    expect(container.querySelector("path")).not.toBeNull();
  });

  it("counts flagged entries in the attention stat", () => {
    render(
      <JournalStats
        entries={[
          makeEntry(
            { entry_type: "symptom", severity: 4, body_area: "paws" },
            { is_concern: true, tags: ["itchy"] },
          ),
        ]}
      />,
    );
    expect(screen.getByText("flag")).toBeInTheDocument();
  });
});
