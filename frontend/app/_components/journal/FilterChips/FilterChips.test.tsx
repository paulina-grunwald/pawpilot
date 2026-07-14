import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DEFAULT_FILTERS, type JournalFilters } from "../FilterSheet";
import { FilterChips } from "./FilterChips";

describe("FilterChips", () => {
  it("marks All as active when no type filter is set", () => {
    render(<FilterChips filters={DEFAULT_FILTERS} onChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Meal" })).toHaveAttribute("aria-pressed", "false");
  });

  it("selects a single type when its chip is clicked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<FilterChips filters={DEFAULT_FILTERS} onChange={onChange} />);

    await user.click(screen.getByRole("button", { name: "Meal" }));

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ entryTypes: ["meal"] }));
  });

  it("toggles an active type back off", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const filters: JournalFilters = { ...DEFAULT_FILTERS, entryTypes: ["meal"] };
    render(<FilterChips filters={filters} onChange={onChange} />);

    await user.click(screen.getByRole("button", { name: "Meal" }));

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ entryTypes: [] }));
  });

  it("clears the type filter when All is clicked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const filters: JournalFilters = { ...DEFAULT_FILTERS, entryTypes: ["meal", "mood"] };
    render(<FilterChips filters={filters} onChange={onChange} />);

    await user.click(screen.getByRole("button", { name: "All" }));

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ entryTypes: [] }));
  });
});
