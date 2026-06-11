import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RangeToggle } from "./RangeToggle";

const OPTIONS = [
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
] as const;

describe("RangeToggle", () => {
  it("renders one button per option with the active one pressed", () => {
    render(<RangeToggle options={OPTIONS} activeDays={7} onChange={() => {}} />);
    expect(screen.getByRole("button", { name: "7d" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "30d" })).toHaveAttribute("aria-pressed", "false");
  });

  it("calls onChange with the clicked option's days", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<RangeToggle options={OPTIONS} activeDays={7} onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: "30d" }));
    expect(onChange).toHaveBeenCalledWith(30);
  });
});
