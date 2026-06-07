import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { TodayPanel, type TodayPanelData } from "./TodayPanel";

const sampleData: TodayPanelData = {
  activityPercent: 78,
  activityLabel: "5h 26m",
  activitySublabel: "78% of 90min goal",
  metrics: [
    { label: "Active", value: "58", unit: "min", delta: "↑ 12 min vs avg", tone: "positive" },
    { label: "Sleep", value: "6h 12m", delta: "↓ 18 min vs avg", tone: "neutral" },
    { label: "Resting HR", value: "68", unit: "bpm" },
    { label: "Respiratory", value: "22", unit: "rpm" },
    { label: "Distance", value: "3.4", unit: "km", delta: "↑ 0.6 km vs avg" },
    { label: "Calm time", value: "4h 50m", delta: "↓ 12 min vs avg" },
  ],
  activityWeekMinutes: [42, 65, 51, 70, 58, 73, 78],
  sleepWeekMinutes: [420, 460, 405, 510, 480, 495, 510],
  activityGoal: 90,
  activityWeekMean: 60,
  sleepWeekMean: 470,
  vitalsStatus: { label: "All vitals normal", tone: "positive" },
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
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(6);
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
