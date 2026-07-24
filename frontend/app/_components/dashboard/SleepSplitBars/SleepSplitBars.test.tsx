import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { SleepSplitBars, type SleepSplitBar } from "./SleepSplitBars";

function makeBars(): SleepSplitBar[] {
  return [
    { date: "2024-05-15", dayLabel: "May 15", nightMinutes: 420, dayMinutes: 90 },
    { date: "2024-05-16", dayLabel: "May 16", nightMinutes: 500, dayMinutes: 60 },
  ];
}

describe("SleepSplitBars", () => {
  it("renders the empty-state message when no bars are provided", () => {
    render(<SleepSplitBars bars={[]} />);
    expect(screen.getByRole("note")).toHaveTextContent(/no sleep data/i);
  });

  it("uses the provided accessible label", () => {
    render(<SleepSplitBars bars={makeBars()} accessibleLabel="custom bars label" />);
    expect(screen.getByRole("img", { name: "custom bars label" })).toBeInTheDocument();
  });

  it("renders one tooltip per bar with night and day breakdown", () => {
    const { container } = render(<SleepSplitBars bars={makeBars()} />);
    const titles = Array.from(container.querySelectorAll("title")).map(
      (node) => node.textContent ?? "",
    );
    // First title is the chart label; the per-bar tooltips follow.
    const barTitles = titles.filter((title) => title.includes("·"));
    expect(barTitles).toHaveLength(2);
    expect(barTitles[0]).toMatch(/May 15.*8h 30m total.*7h 00m night.*1h 30m day/);
    expect(barTitles[1]).toMatch(/May 16.*9h 20m total.*8h 20m night.*1h 00m day/);
  });

  it("shows a hover tooltip breaking out night and day for the hovered bar", () => {
    render(<SleepSplitBars bars={makeBars()} accessibleLabel="sleep bars" />);
    const svg = screen.getByRole("img", { name: "sleep bars" });
    // No tooltip until the pointer enters the plot.
    expect(screen.queryByText(/^night 7h 00m$/)).not.toBeInTheDocument();
    // Hover near the left edge to land on the first bar.
    fireEvent.pointerMove(svg, { clientX: 60, clientY: 100 });
    expect(screen.getByText(/^night 7h 00m$/)).toBeInTheDocument();
    expect(screen.getByText(/^day naps 1h 30m$/)).toBeInTheDocument();
    // Leaving clears the tooltip.
    fireEvent.pointerLeave(svg);
    expect(screen.queryByText(/^night 7h 00m$/)).not.toBeInTheDocument();
  });

  it("renders a legend for night and day", () => {
    render(<SleepSplitBars bars={makeBars()} />);
    expect(screen.getByText(/^night$/i)).toBeInTheDocument();
    expect(screen.getByText(/^day naps$/i)).toBeInTheDocument();
  });

  it("only labels every Nth x-tick when there are many bars", () => {
    const manyBars: SleepSplitBar[] = Array.from({ length: 30 }, (_, index) => ({
      date: `2024-05-${String(index + 1).padStart(2, "0")}`,
      dayLabel: `May ${index + 1}`,
      nightMinutes: 400 + index,
      dayMinutes: 60,
    }));
    const { container } = render(<SleepSplitBars bars={manyBars} />);
    const labels = Array.from(container.querySelectorAll("text"))
      .map((node) => node.textContent ?? "")
      .filter((text) => text.startsWith("May "));
    // With 30 bars we expect a stride to thin out date labels.
    expect(labels.length).toBeLessThan(30);
    expect(labels.length).toBeGreaterThan(0);
  });
});
