import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SubmitButton } from "./SubmitButton";

describe("SubmitButton", () => {
  it("renders children as label when not submitting", () => {
    render(<SubmitButton>Sign up</SubmitButton>);
    expect(screen.getByRole("button", { name: "Sign up" })).toBeEnabled();
  });

  it("disables and sets aria-busy when isSubmitting", () => {
    render(<SubmitButton isSubmitting>Sign up</SubmitButton>);
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });

  it("renders sr-only loading label when isSubmitting", () => {
    render(
      <SubmitButton isSubmitting loadingLabel="Submitting…">
        Sign up
      </SubmitButton>,
    );
    expect(screen.getByText("Submitting…")).toHaveClass("sr-only");
  });

  it("respects the disabled prop when not submitting", () => {
    render(<SubmitButton disabled>Sign up</SubmitButton>);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("calls onClick when the user clicks it", async () => {
    const user = userEvent.setup();
    let clicked = false;
    render(
      <SubmitButton
        onClick={() => {
          clicked = true;
        }}
      >
        Sign up
      </SubmitButton>,
    );
    await user.click(screen.getByRole("button"));
    expect(clicked).toBe(true);
  });
});
