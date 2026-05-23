import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Chip } from "./Chip";

describe("Chip", () => {
  it("renders children", () => {
    render(<Chip>Adult</Chip>);
    expect(screen.getByText("Adult")).toBeInTheDocument();
  });

  it("applies the variant class for each variant", () => {
    const variants = ["default", "blue", "forest", "ochre", "dark"] as const;
    for (const variant of variants) {
      const { unmount } = render(<Chip variant={variant}>{variant}</Chip>);
      const node = screen.getByText(variant);
      expect(node.className).toMatch(new RegExp(variant));
      unmount();
    }
  });
});
