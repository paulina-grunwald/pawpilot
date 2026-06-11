import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  DEFAULT_FILTERS,
  FilterSheet,
  countActiveFilters,
  dateRangeToOccurredFrom,
  type JournalFilters,
} from "./FilterSheet";

function renderSheet(filters: JournalFilters = DEFAULT_FILTERS, totalMatching: number | null = 18) {
  const onChange = vi.fn();
  const onClose = vi.fn();
  render(
    <FilterSheet
      open
      filters={filters}
      totalMatching={totalMatching}
      onChange={onChange}
      onClose={onClose}
    />,
  );
  return { onChange, onClose };
}

describe("FilterSheet", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <FilterSheet
        open={false}
        filters={DEFAULT_FILTERS}
        totalMatching={null}
        onChange={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("toggles an entry type into the filters", async () => {
    const user = userEvent.setup();
    const { onChange } = renderSheet();

    await user.click(screen.getByRole("button", { name: "Symptom" }));

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ entryTypes: ["symptom"] }),
    );
  });

  it("selects a date range preset", async () => {
    const user = userEvent.setup();
    const { onChange } = renderSheet();

    await user.click(screen.getByRole("radio", { name: "Last 7 days" }));

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ dateRange: "7d" }));
  });

  it("toggles concerns only", async () => {
    const user = userEvent.setup();
    const { onChange } = renderSheet();

    await user.click(screen.getByLabelText(/Concerns only/i));

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ concernsOnly: true }));
  });

  it("resets back to the defaults", async () => {
    const user = userEvent.setup();
    const { onChange } = renderSheet({
      entryTypes: ["meal"],
      dateRange: "7d",
      concernsOnly: true,
    });

    await user.click(screen.getByRole("button", { name: "Reset" }));

    expect(onChange).toHaveBeenCalledWith(DEFAULT_FILTERS);
  });

  it("shows the live matching count on the CTA and closes on apply", async () => {
    const user = userEvent.setup();
    const { onClose } = renderSheet(DEFAULT_FILTERS, 18);

    const applyButton = screen.getByRole("button", { name: "Show 18 matching entries" });
    await user.click(applyButton);

    expect(onClose).toHaveBeenCalled();
  });
});

describe("countActiveFilters", () => {
  it("counts types, non-default range and concerns toggle", () => {
    expect(countActiveFilters(DEFAULT_FILTERS)).toBe(0);
    expect(
      countActiveFilters({ entryTypes: ["meal", "mood"], dateRange: "7d", concernsOnly: true }),
    ).toBe(4);
  });
});

describe("dateRangeToOccurredFrom", () => {
  const now = new Date("2026-06-11T14:00:00Z");

  it("returns undefined for all-time", () => {
    expect(dateRangeToOccurredFrom("all", now)).toBeUndefined();
  });

  it("returns midnight for today", () => {
    const from = dateRangeToOccurredFrom("today", now);
    expect(new Date(from as string).getHours()).toBe(0);
  });

  it("returns a date 7 days back for 7d", () => {
    const from = dateRangeToOccurredFrom("7d", now);
    const diffDays =
      (now.getTime() - new Date(from as string).getTime()) / (1000 * 60 * 60 * 24);
    expect(Math.round(diffDays)).toBe(7);
  });
});
