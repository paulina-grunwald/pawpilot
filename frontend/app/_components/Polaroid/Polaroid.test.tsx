import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Polaroid } from "./Polaroid";

describe("Polaroid", () => {
  it("renders the image with alt text and caption", () => {
    render(<Polaroid src="/img/sunset-dog.webp" alt="Test dog" caption="Haru" />);
    expect(screen.getByAltText("Test dog")).toBeInTheDocument();
    expect(screen.getByText("Haru")).toBeInTheDocument();
  });

  it("applies rotation transform from the rotate prop", () => {
    const { container } = render(<Polaroid src="/img/sunset-dog.webp" rotate={12} />);
    const card = container.firstChild as HTMLElement;
    expect(card.style.transform).toBe("rotate(12deg)");
  });

  it("renders the sticker child", () => {
    render(<Polaroid src="/img/sunset-dog.webp" sticker={<span data-testid="sticker">!</span>} />);
    expect(screen.getByTestId("sticker")).toBeInTheDocument();
  });

  it("optimizes images by default (unoptimized=false)", () => {
    const { container } = render(<Polaroid src="/img/sunset-dog.webp" alt="Test" />);
    const image = container.querySelector("img")!;
    // Next/Image rewrites the src for optimization unless unoptimized is set.
    expect(image.getAttribute("src")).toContain("_next/image");
  });
});
