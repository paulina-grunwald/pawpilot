import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Sticker } from "./Sticker";

describe("Sticker", () => {
  it("renders children with rotation and color", () => {
    const { container } = render(
      <Sticker color="var(--blue)" rotate={-10} top={0} left={0}>
        Hello
      </Sticker>,
    );
    expect(screen.getByText("Hello")).toBeInTheDocument();
    const sticker = container.firstChild as HTMLElement;
    expect(sticker.style.background).toBe("var(--blue)");
    expect(sticker.style.transform).toBe("rotate(-10deg)");
    expect(sticker.style.top).toBe("0px");
    expect(sticker.style.left).toBe("0px");
  });

  it("falls back to default color and rotation", () => {
    const { container } = render(<Sticker>Default</Sticker>);
    const sticker = container.firstChild as HTMLElement;
    expect(sticker.style.background).toBe("var(--blue)");
    expect(sticker.style.transform).toBe("rotate(-8deg)");
  });
});
