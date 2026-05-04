import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { DebateMini } from "./DebateMini";

describe("DebateMini", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("reveals messages progressively over time", () => {
    const { container } = render(<DebateMini />);
    const messageRows = container.firstElementChild!.children;
    expect(messageRows.length).toBe(4);
    expect(messageRows[0].getAttribute("style") ?? "").toMatch(/opacity:\s*0\.15/);

    act(() => {
      vi.advanceTimersByTime(2200);
    });
    expect(messageRows[0].getAttribute("style") ?? "").toMatch(/opacity:\s*1/);
  });

  it("renders all four speaker roles", () => {
    render(<DebateMini />);
    expect(screen.getAllByText(/researcher/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/skeptic/i)).toBeInTheDocument();
    expect(screen.getByText(/synth/i)).toBeInTheDocument();
  });
});
