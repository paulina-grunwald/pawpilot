import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { LineChart } from "./LineChart";

describe("LineChart", () => {
  it("renders nothing visible when fewer than 2 values are provided", () => {
    const { container } = render(<LineChart values={[5]} />);
    expect(container.querySelector("svg")).toBeNull();
  });

  it("renders an SVG with the accessible label when given values", () => {
    render(
      <LineChart
        values={[10, 12, 8, 15, 18, 22, 24]}
        accessibleLabel="Activity, past 7 days"
      />,
    );
    expect(screen.getByRole("img", { name: /activity, past 7 days/i })).toBeInTheDocument();
  });

  it("renders the legend by default", () => {
    render(<LineChart values={[1, 2, 3, 4]} />);
    expect(screen.getByText(/this week/i)).toBeInTheDocument();
  });

  it("hides the legend in compact mode", () => {
    render(<LineChart values={[1, 2, 3, 4]} compact />);
    expect(screen.queryByText(/this week/i)).not.toBeInTheDocument();
  });

  it("includes goal label when a goal is provided", () => {
    render(<LineChart values={[1, 2, 3, 4]} goal={5} />);
    expect(screen.getByText(/goal 5/i)).toBeInTheDocument();
  });

  it("shows the hovered point's value in the tooltip", () => {
    render(
      <LineChart
        values={[10, 20, 30, 40]}
        yFormat={(value) => `${value} min`}
        accessibleLabel="Activity"
      />,
    );
    const svg = screen.getByRole("img", { name: /activity/i });
    // Default (no hover) shows the latest value.
    expect(screen.getByText(/40 min/)).toBeInTheDocument();
    // Hover near the left edge to select the first point.
    fireEvent.pointerMove(svg, { clientX: 0, clientY: 50 });
    expect(screen.getByText(/10 min/)).toBeInTheDocument();
    // Leaving the chart restores the latest-value tooltip.
    fireEvent.pointerLeave(svg);
    expect(screen.getByText(/40 min/)).toBeInTheDocument();
  });

  it("renders the provided weekday labels instead of a fixed Monday-start week", () => {
    // Data covering Thu -> Wed (Jul 9-15, 2026): the last day is Wednesday, not Sunday.
    const days = ["Th", "Fr", "Sa", "Su", "Mo", "Tu", "We"];
    render(<LineChart values={[1, 2, 3, 4, 5, 6, 7]} days={days} accessibleLabel="Activity" />);
    // The first and last labels are always drawn; they prove labels follow the
    // real weekday (Th -> We) rather than the hardcoded Mo -> Su default.
    expect(screen.getByText("Th")).toBeInTheDocument();
    expect(screen.getByText("We")).toBeInTheDocument();
    expect(screen.queryByText("Su")).not.toBeInTheDocument();
    expect(screen.queryByText("Mo")).not.toBeInTheDocument();
  });

  it("thins x-axis date labels for long ranges", () => {
    const values = Array.from({ length: 90 }, (_, index) => index);
    const dates = Array.from({ length: 90 }, (_, index) => `d${index}`);
    render(<LineChart values={values} dates={dates} accessibleLabel="Activity" />);
    const renderedDateLabels = dates.filter(
      (date) => screen.queryAllByText(date).length > 0,
    );
    // Far fewer than all 90 labels are drawn, but the latest day is kept.
    expect(renderedDateLabels.length).toBeLessThan(90);
    expect(screen.queryAllByText("d89").length).toBeGreaterThan(0);
  });
});
