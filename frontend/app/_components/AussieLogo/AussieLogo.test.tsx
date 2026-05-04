import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { AussieLogo } from "./AussieLogo";

describe("AussieLogo", () => {
  it("uses the paper token for color by default and applies custom size", () => {
    const { container } = render(<AussieLogo size={48} />);
    const svg = container.querySelector("svg")!;
    expect(svg).toHaveAttribute("width", "48");
    expect(svg).toHaveAttribute("height", "48");
    expect(svg.getAttribute("stroke")).toBe("var(--paper)");
  });

  it("respects custom color", () => {
    const { container } = render(<AussieLogo color="var(--blue)" />);
    const svg = container.querySelector("svg")!;
    expect(svg.getAttribute("stroke")).toBe("var(--blue)");
  });
});
