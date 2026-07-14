import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { Sparkline } from "./Sparkline";

describe("Sparkline", () => {
  it("renders nothing with fewer than two values", () => {
    const { container } = render(<Sparkline values={[5]} />);
    expect(container.querySelector("svg")).toBeNull();
  });

  it("draws a path and an end marker for a series", () => {
    const { container } = render(<Sparkline values={[3, 1, 4, 2]} />);
    expect(container.querySelector("path")).not.toBeNull();
    expect(container.querySelector("circle")).not.toBeNull();
  });

  it("handles a flat series without dividing by zero", () => {
    const { container } = render(<Sparkline values={[2, 2, 2]} />);
    const path = container.querySelector("path");
    expect(path?.getAttribute("d")).not.toContain("NaN");
  });
});
