import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Field } from "./Field";

describe("Field", () => {
  it("renders label associated with input by id", () => {
    render(<Field label="Email" name="email" type="email" />);
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("type", "email");
    expect(input).toHaveAttribute("id", "field-email");
  });

  it("renders helpText when no error is present", () => {
    render(
      <Field label="Password" name="password" helpText="At least 8 characters" />,
    );
    const input = screen.getByLabelText("Password");
    expect(screen.getByText("At least 8 characters")).toBeInTheDocument();
    expect(input).toHaveAttribute("aria-describedby", "field-password-help");
  });

  it("renders error and sets aria-invalid + aria-describedby", () => {
    render(
      <Field label="Email" name="email" error="Email is required" />,
    );
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAttribute("aria-describedby", "field-email-error");
    const error = screen.getByRole("alert");
    expect(error).toHaveTextContent("Email is required");
  });

  it("hides helpText when an error is present", () => {
    render(
      <Field
        label="Password"
        name="password"
        helpText="At least 8 characters"
        error="Password is required"
      />,
    );
    expect(screen.queryByText("At least 8 characters")).not.toBeInTheDocument();
  });

  it("omits the help id from aria-describedby when help text is hidden by error", () => {
    render(
      <Field
        label="Password"
        name="password"
        helpText="At least 8 characters"
        error="Password is required"
      />,
    );
    const input = screen.getByLabelText("Password");
    expect(input).toHaveAttribute("aria-describedby", "field-password-error");
  });

  it("forwards arbitrary props to the input (autoComplete, type)", () => {
    render(
      <Field
        label="Password"
        name="password"
        type="password"
        autoComplete="current-password"
      />,
    );
    const input = screen.getByLabelText("Password");
    expect(input).toHaveAttribute("type", "password");
    expect(input).toHaveAttribute("autocomplete", "current-password");
  });
});
