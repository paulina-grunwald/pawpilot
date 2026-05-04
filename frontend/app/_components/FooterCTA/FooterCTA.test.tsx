import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { FooterCTA } from "./FooterCTA";

describe("FooterCTA waitlist form", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders policy links pointing to real routes", () => {
    render(<FooterCTA />);
    expect(screen.getByRole("link", { name: /privacy/i })).toHaveAttribute("href", "/privacy");
    expect(screen.getByRole("link", { name: /terms/i })).toHaveAttribute("href", "/terms");
  });

  it("ignores invalid emails (stays in idle)", () => {
    const { container } = render(<FooterCTA />);
    const input = screen.getByLabelText(/email/i);
    const form = container.querySelector("form")!;
    fireEvent.change(input, { target: { value: "still-bad" } });
    fireEvent.submit(form);
    expect(screen.getByRole("button", { name: /join the waitlist/i })).toBeInTheDocument();
  });

  it("transitions to done on a valid email", () => {
    const { container } = render(<FooterCTA />);
    const input = screen.getByLabelText(/email/i);
    const form = container.querySelector("form")!;
    fireEvent.change(input, { target: { value: "owner@yourdog.house" } });
    fireEvent.submit(form);
    expect(screen.getByRole("button", { name: /sending/i })).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(700);
    });
    expect(screen.getByRole("button", { name: /see you soon/i })).toBeInTheDocument();
  });
});
