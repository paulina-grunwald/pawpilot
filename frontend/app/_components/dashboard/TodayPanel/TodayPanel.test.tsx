import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { TodayPanel, type TodayPanelData } from "./TodayPanel";

const sampleData: TodayPanelData = {
  activityPercent: 78,
  innerActivityPercent: 64,
  activityLabel: "78%",
  activitySublabel: "of daily goal",
  metrics: [
    { label: "Active", value: "58", unit: "min", delta: "+12 vs avg", tone: "positive" },
    { label: "Rest", value: "6h 12m", delta: "↓ 18 min", tone: "neutral" },
    { label: "Resting HR", value: "68", unit: "bpm", delta: "within baseline" },
    { label: "Respiratory", value: "22", unit: "rpm", delta: "within baseline" },
  ],
  activityWeekMinutes: [42, 65, 51, 70, 58, 73, 78],
  sleepWeekMinutes: [420, 460, 405, 510, 480, 495, 510],
};

describe("TodayPanel", () => {
  it("renders the placeholder mode when no data is provided", () => {
    render(<TodayPanel petName="Luna" todayLabel="Sat, May 23" />);
    expect(
      screen.getByRole("heading", { name: /connect tractive to see luna/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/wearable not connected/i)).toBeInTheDocument();
    expect(
      screen.getByText(/connect tractive to see today/i),
    ).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(4);
    expect(screen.getAllByRole("note").length).toBe(2);
  });

  it("renders real data and stat values when data is provided", () => {
    render(<TodayPanel petName="Luna" todayLabel="Sat, May 23" data={sampleData} />);
    expect(
      screen.getByRole("heading", { name: /luna.*on track/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/all vitals normal/i)).toBeInTheDocument();
    expect(screen.getByText("58")).toBeInTheDocument();
    expect(screen.getByText("68")).toBeInTheDocument();
    expect(
      screen.queryByText(/connect tractive to see today/i),
    ).not.toBeInTheDocument();
  });

  it("shows the today's label in the eyebrow", () => {
    render(<TodayPanel petName="Luna" todayLabel="Sat, May 23" />);
    expect(screen.getByText(/today — sat, may 23/i)).toBeInTheDocument();
  });
});
