import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { BirthdayField } from "./BirthdayField";

function ControlledHarness({ initial = "" }: { initial?: string }) {
  const [value, setValue] = useState(initial);
  return <BirthdayField value={value} onChange={setValue} />;
}

describe("BirthdayField", () => {
  it("shows 'Pick a date' placeholder when no value is set", () => {
    render(<ControlledHarness />);
    expect(screen.getByRole("button", { name: /pick a date/i })).toBeInTheDocument();
  });

  it("renders the formatted date when a value is set", () => {
    render(<ControlledHarness initial="2021-06-14" />);
    expect(screen.getByRole("button")).toHaveTextContent(/jun 14, 2021/i);
  });

  it("opens a dialog when clicked", async () => {
    const user = userEvent.setup();
    render(<ControlledHarness />);
    await user.click(screen.getByRole("button"));
    expect(screen.getByRole("dialog", { name: /choose birthday/i })).toBeInTheDocument();
  });

  it("closes the dialog when Escape is pressed and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    render(<ControlledHarness />);
    const trigger = screen.getByRole("button");
    await user.click(trigger);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("calls onChange with an ISO date when a day is selected", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<BirthdayField value="2021-06-14" onChange={onChange} />);
    await user.click(screen.getByRole("button"));
    const gridcells = screen.getAllByRole("gridcell");
    const selectableCell = gridcells.find((cell) => {
      const button = cell.querySelector("button");
      return button && !button.hasAttribute("disabled");
    });
    expect(selectableCell).toBeDefined();
    const dayButton = selectableCell!.querySelector("button")!;
    await user.click(dayButton);
    expect(onChange).toHaveBeenCalledWith(expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/));
  });

  it("flags itself with data-invalid when invalid is true (no aria-invalid on button)", () => {
    render(<BirthdayField value="" onChange={() => {}} invalid />);
    const button = screen.getByRole("button");
    expect(button).toHaveAttribute("data-invalid", "true");
    expect(button).not.toHaveAttribute("aria-invalid");
  });
});
