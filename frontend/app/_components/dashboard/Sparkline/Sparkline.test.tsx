import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Sparkline } from "./Sparkline";

describe("Sparkline", () => {
  it("renders an SVG with an accessible label", () => {
    render(<Sparkline values={[1, 2, 3, 4]} accessibleLabel="Daily steps" />);
    const svg = screen.getByRole("img", { name: "Daily steps" });
    expect(svg.tagName).toBe("svg");
  });

  it("falls back to a value-based label when none is provided", () => {
    render(<Sparkline values={[10, 20, 30]} />);
    expect(screen.getByRole("img", { name: /latest value 30/i })).toBeInTheDocument();
  });

  it("renders an empty placeholder when fewer than two values are provided", () => {
    const { container } = render(<Sparkline values={[5]} />);
    expect(container.querySelector("svg")).toBeNull();
  });

  it("includes a line path and an end-point circle", () => {
    const { container } = render(<Sparkline values={[1, 3, 2, 5]} />);
    expect(container.querySelectorAll("path").length).toBeGreaterThanOrEqual(1);
    expect(container.querySelector("circle")).not.toBeNull();
  });
});
