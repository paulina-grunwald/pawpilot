import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ChatBubble } from "./ChatBubble";

describe("ChatBubble", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("rotates through queries on the interval", () => {
    render(<ChatBubble />);
    expect(screen.getByText(/Did Haru just eat a grape/i)).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(4500);
    });
    expect(screen.getByText(/rash on her belly/i)).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(4500);
    });
    expect(screen.getByText(/limping after our morning walk/i)).toBeInTheDocument();
  });

  it("renders citation entries with their sources", () => {
    render(<ChatBubble />);
    expect(screen.getByText(/ACVIM Toxicology Guidelines, 2023/)).toBeInTheDocument();
    expect(screen.getByText(/Haru's bloodwork/)).toBeInTheDocument();
  });
});
