import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QuickActions } from "./QuickActions";

vi.mock("@/lib/journal", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/journal")>();
  return {
    ...actual,
    createJournalEntry: vi.fn(),
    updateJournalEntry: vi.fn(),
  };
});

describe("QuickActions", () => {
  it("renders the quick-log row with a journal link", () => {
    render(<QuickActions petId="pet-1" petName="Luna" />);

    expect(screen.getByRole("button", { name: "Log meal" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Log bathroom" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Note symptom" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Log mood" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Journal →" })).toHaveAttribute(
      "href",
      "/pets/pet-1/journal",
    );
  });

  it("opens the modal pre-selected to the tapped type", async () => {
    const user = userEvent.setup();
    render(<QuickActions petId="pet-1" petName="Luna" />);

    await user.click(screen.getByRole("button", { name: "Note symptom" }));

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save symptom" })).toBeInTheDocument();
  });

  it("opens the type picker from More…", async () => {
    const user = userEvent.setup();
    render(<QuickActions petId="pet-1" petName="Luna" />);

    await user.click(screen.getByRole("button", { name: "More…" }));

    expect(screen.getByRole("heading", { name: "What happened?" })).toBeInTheDocument();
  });
});
