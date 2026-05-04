import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { Hero } from "./Hero";

describe("Hero waitlist form", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the headline and CTA", () => {
    render(<Hero />);
    expect(
      screen.getByRole("heading", { level: 1, name: /can't stop worrying about/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save my spot/i })).toBeInTheDocument();
  });

  it("shows an error message for an invalid email", () => {
    const { container } = render(<Hero />);
    const input = screen.getByLabelText(/email/i);
    const form = container.querySelector("form")!;
    fireEvent.change(input, { target: { value: "not-an-email" } });
    fireEvent.submit(form);
    expect(screen.getByText(/email doesn't quite look right/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("clears the error state when the user edits the email again", () => {
    const { container } = render(<Hero />);
    const input = screen.getByLabelText(/email/i);
    const form = container.querySelector("form")!;
    fireEvent.change(input, { target: { value: "bad" } });
    fireEvent.submit(form);
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    fireEvent.change(input, { target: { value: "bad@" } });
    expect(screen.getByRole("button", { name: /save my spot/i })).toBeInTheDocument();
  });

  it("transitions through sending → done on a valid email", () => {
    const { container } = render(<Hero />);
    const input = screen.getByLabelText(/email/i);
    const form = container.querySelector("form")!;
    fireEvent.change(input, { target: { value: "owner@yourdog.house" } });
    fireEvent.submit(form);
    expect(screen.getByRole("button", { name: /sending/i })).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(800);
    });
    expect(screen.getByRole("button", { name: /you're in/i })).toBeInTheDocument();
  });
});
