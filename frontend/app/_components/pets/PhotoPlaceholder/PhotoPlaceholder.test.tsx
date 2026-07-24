import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PhotoPlaceholder } from "./PhotoPlaceholder";

describe("PhotoPlaceholder", () => {
  it("renders the default label", () => {
    render(<PhotoPlaceholder />);
    expect(screen.getByText("dog photo")).toBeInTheDocument();
  });

  it("renders a custom label", () => {
    render(<PhotoPlaceholder label="Luna" />);
    expect(screen.getByText("Luna")).toBeInTheDocument();
  });

  it("applies width, height, and radius via inline style", () => {
    const { container } = render(<PhotoPlaceholder label="x" width={80} height={80} radius={20} />);
    const root = container.firstElementChild as HTMLElement;
    expect(root.style.width).toBe("80px");
    expect(root.style.height).toBe("80px");
    expect(root.style.borderRadius).toBe("20px");
  });

  it("is aria-hidden so screen readers skip it", () => {
    const { container } = render(<PhotoPlaceholder />);
    expect(container.firstElementChild).toHaveAttribute("aria-hidden");
  });
});
