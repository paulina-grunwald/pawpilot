import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ActivityRing } from "./ActivityRing";

describe("ActivityRing", () => {
  it("uses the provided accessibleLabel as aria-label", () => {
    render(
      <ActivityRing
        percent={45}
        label="45%"
        sublabel="of goal"
        accessibleLabel="Daily activity 45%"
      />,
    );
    expect(screen.getByRole("img", { name: /daily activity 45%/i })).toBeInTheDocument();
  });

  it("falls back to label + sublabel for aria-label when no accessibleLabel is given", () => {
    render(<ActivityRing percent={20} label="20%" sublabel="of daily goal" />);
    expect(screen.getByRole("img", { name: /20% of daily goal/i })).toBeInTheDocument();
  });

  it("renders the label text in the center", () => {
    render(<ActivityRing percent={78} label="78%" sublabel="of daily goal" />);
    expect(screen.getByText("78%")).toBeInTheDocument();
    expect(screen.getByText("of daily goal")).toBeInTheDocument();
  });

  it("caps the visual ring fill at 100% even when percent is much higher", () => {
    const { container } = render(
      <ActivityRing percent={425} label="5h 26m" sublabel="425% — goal smashed" size={200} />,
    );
    // The filled circle uses strokeDasharray="<filled> <gap>". Find the
    // foreground stroked circle and assert filled portion ≈ full circumference.
    const circles = container.querySelectorAll("circle[stroke-dasharray]");
    expect(circles.length).toBeGreaterThan(0);
    const dashArrayValue = circles[circles.length - 1].getAttribute("stroke-dasharray") ?? "";
    const [filled, gap] = dashArrayValue.split(" ").map(Number);
    // Visual cap means the gap should be ~0 when at or above 100%.
    expect(gap).toBeLessThan(0.0001);
    expect(filled).toBeGreaterThan(0);
  });
});
