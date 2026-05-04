import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { BaseIcon } from "./BaseIcon";
import { ArrowRightIcon } from "./ArrowRightIcon";
import { CheckIcon } from "./CheckIcon";
import { AlertIcon } from "./AlertIcon";

describe("BaseIcon", () => {
  it("applies size, color, strokeWidth and viewBox", () => {
    const { container } = render(
      <BaseIcon size={32} color="var(--blue)" strokeWidth={3} viewBox="0 0 32 32">
        <path d="M0 0h10" />
      </BaseIcon>,
    );
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute("width", "32");
    expect(svg).toHaveAttribute("height", "32");
    expect(svg).toHaveAttribute("stroke", "var(--blue)");
    expect(svg).toHaveAttribute("stroke-width", "3");
    expect(svg).toHaveAttribute("viewBox", "0 0 32 32");
    expect(svg).toHaveAttribute("aria-hidden", "true");
  });

  it("uses sensible defaults", () => {
    const { container } = render(
      <BaseIcon>
        <path d="M0 0h1" />
      </BaseIcon>,
    );
    const svg = container.querySelector("svg")!;
    expect(svg).toHaveAttribute("width", "24");
    expect(svg).toHaveAttribute("stroke", "currentColor");
    expect(svg).toHaveAttribute("viewBox", "0 0 24 24");
  });

  it("forwards extra svg props", () => {
    const { container } = render(
      <BaseIcon className="custom" data-testid="icon">
        <path d="M0 0h1" />
      </BaseIcon>,
    );
    const svg = container.querySelector("svg")!;
    expect(svg).toHaveClass("custom");
    expect(svg).toHaveAttribute("data-testid", "icon");
  });
});

describe("Specific icons", () => {
  it("ArrowRightIcon defaults to size 16, strokeWidth 2", () => {
    const { container } = render(<ArrowRightIcon />);
    const svg = container.querySelector("svg")!;
    expect(svg).toHaveAttribute("width", "16");
    expect(svg).toHaveAttribute("stroke-width", "2");
  });

  it("CheckIcon defaults to size 14, strokeWidth 2.4", () => {
    const { container } = render(<CheckIcon />);
    const svg = container.querySelector("svg")!;
    expect(svg).toHaveAttribute("width", "14");
    expect(svg).toHaveAttribute("stroke-width", "2.4");
  });

  it("AlertIcon respects color override", () => {
    const { container } = render(<AlertIcon color="var(--ochre)" />);
    const svg = container.querySelector("svg")!;
    expect(svg).toHaveAttribute("stroke", "var(--ochre)");
  });
});
