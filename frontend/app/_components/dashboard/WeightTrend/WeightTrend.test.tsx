import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import type { WeightSeriesPoint } from "@/lib/weight";
import { WeightTrend } from "./WeightTrend";

function makeSeries(): WeightSeriesPoint[] {
  return [
    { date: "2024-05-17", label: "May 17", weightGrams: 27200 },
    { date: "2024-05-20", label: "May 20", weightGrams: 27400 },
    { date: "2024-05-23", label: "May 23", weightGrams: 27600 },
  ];
}

describe("WeightTrend", () => {
  it("shows a loading note while the series is undefined", () => {
    render(<WeightTrend series={undefined} rangeLabel="7d" />);
    expect(screen.getByRole("note")).toHaveTextContent(/loading weight history/i);
  });

  it("prompts to log weight when the series is empty", () => {
    render(<WeightTrend series={[]} rangeLabel="7d" />);
    expect(screen.getByRole("note")).toHaveTextContent(/log weight entries/i);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("explains that one reading is not enough for a trend", () => {
    render(
      <WeightTrend
        series={[{ date: "2024-05-23", label: "May 23", weightGrams: 27600 }]}
        rangeLabel="7d"
      />,
    );
    expect(screen.getByRole("note")).toHaveTextContent(/one weigh-in logged/i);
  });

  it("renders the chart and the latest weight when there are enough points", () => {
    render(<WeightTrend series={makeSeries()} rangeLabel="30d" />);
    // Latest weight shows in the headline (and the chart's default callout).
    expect(screen.getAllByText("27.6 kg").length).toBeGreaterThan(0);
    expect(screen.getByRole("img", { name: /weight over the past 30d/i })).toBeInTheDocument();
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });

  it("shows a hovered reading in the chart tooltip", () => {
    render(<WeightTrend series={makeSeries()} rangeLabel="30d" />);
    const chart = screen.getByRole("img", { name: /weight over the past 30d/i });
    fireEvent.pointerMove(chart, { clientX: 0, clientY: 50 });
    // Leftmost point is the first reading.
    expect(screen.getAllByText("27.2 kg").length).toBeGreaterThan(0);
  });
});
