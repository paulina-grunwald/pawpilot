import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { CollarMini } from "./CollarMini";

describe("CollarMini", () => {
  it("renders the live header, walk label and 24 bars", () => {
    const { container } = render(<CollarMini />);
    expect(screen.getByText(/Live · last 24h/)).toBeInTheDocument();
    expect(screen.getByText(/walk · 18 min/)).toBeInTheDocument();
    const bars = container.querySelectorAll("div[style*='flex: 1']");
    expect(bars.length).toBe(24);
  });
});
