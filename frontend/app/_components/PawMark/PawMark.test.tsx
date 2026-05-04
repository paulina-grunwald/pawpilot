import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { PawMark } from "./PawMark";

describe("PawMark", () => {
  it("renders the badge variant by default", () => {
    const { container } = render(<PawMark />);
    const image = container.querySelector("img")!;
    expect(image.getAttribute("src")).toContain("pawdoc-logo.png");
  });

  it("renders the wordmark variant when requested", () => {
    const { container } = render(<PawMark variant="wordmark" />);
    const image = container.querySelector("img")!;
    expect(image.getAttribute("src")).toContain("pawdoc-logo-v2.png");
  });

  it("respects size and className", () => {
    const { container } = render(<PawMark size={120} className="custom-mark" />);
    const image = container.querySelector("img")!;
    expect(image).toHaveClass("custom-mark");
    expect(image.style.height).toBe("120px");
  });
});
