import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRef } from "react";
import { useFocusTrap } from "./useFocusTrap";

function TrapHarness({ active = true }: { active?: boolean }) {
  const containerRef = useRef<HTMLDivElement>(null);
  useFocusTrap(containerRef, active);
  return (
    <div>
      <button type="button">outside-before</button>
      <div ref={containerRef} tabIndex={-1}>
        <button type="button">first</button>
        <button type="button">second</button>
        <button type="button">third</button>
      </div>
      <button type="button">outside-after</button>
    </div>
  );
}

describe("useFocusTrap", () => {
  it("wraps focus to the first element when tabbing past the last", async () => {
    const user = userEvent.setup();
    render(<TrapHarness />);
    const first = screen.getByRole("button", { name: "first" });
    const third = screen.getByRole("button", { name: "third" });

    third.focus();
    await user.tab();
    expect(first).toHaveFocus();
  });

  it("wraps focus to the last element when shift-tabbing before the first", async () => {
    const user = userEvent.setup();
    render(<TrapHarness />);
    const first = screen.getByRole("button", { name: "first" });
    const third = screen.getByRole("button", { name: "third" });

    first.focus();
    await user.tab({ shift: true });
    expect(third).toHaveFocus();
  });

  it("lets focus move normally between interior elements", async () => {
    const user = userEvent.setup();
    render(<TrapHarness />);
    const first = screen.getByRole("button", { name: "first" });
    const second = screen.getByRole("button", { name: "second" });

    first.focus();
    await user.tab();
    expect(second).toHaveFocus();
  });

  it("does not trap focus when inactive", async () => {
    const user = userEvent.setup();
    render(<TrapHarness active={false} />);
    const third = screen.getByRole("button", { name: "third" });
    const outsideAfter = screen.getByRole("button", { name: "outside-after" });

    third.focus();
    await user.tab();
    expect(outsideAfter).toHaveFocus();
  });
});
