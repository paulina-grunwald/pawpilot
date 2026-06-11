import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PetActionButton } from "./PetActionButton";

describe("PetActionButton", () => {
  it("renders children and defaults to type=button", () => {
    render(<PetActionButton>Click</PetActionButton>);
    const button = screen.getByRole("button", { name: /click/i });
    expect(button).toHaveAttribute("type", "button");
  });

  it("forwards click handler", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<PetActionButton onClick={onClick}>Go</PetActionButton>);
    await user.click(screen.getByRole("button", { name: /go/i }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("respects disabled prop", () => {
    render(<PetActionButton disabled>Locked</PetActionButton>);
    expect(screen.getByRole("button", { name: /locked/i })).toBeDisabled();
  });

  it("applies variant CSS class", () => {
    for (const variant of ["default", "primary", "danger"] as const) {
      const { unmount } = render(<PetActionButton variant={variant}>{variant}</PetActionButton>);
      const button = screen.getByRole("button", { name: variant });
      expect(button.className).toMatch(new RegExp(variant));
      unmount();
    }
  });
});
