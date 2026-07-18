import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { OutingsCardData } from "@/lib/tractive.format";
import { OutingsCard } from "./OutingsCard";

function makeData(overrides: Partial<OutingsCardData> = {}): OutingsCardData {
  return {
    latestDayLabel: "May 23",
    latestCount: 3,
    latestRows: [
      {
        startLabel: "07:40",
        durationLabel: "at least 32 min",
        distanceLabel: "up to 0.8 km away",
      },
      {
        startLabel: "18:05",
        durationLabel: "at least 25 min",
        distanceLabel: "up to 0.5 km away",
      },
    ],
    rangeDailyAverage: 2.8,
    daysInRange: 25,
    ...overrides,
  };
}

describe("OutingsCard", () => {
  it("renders the connect placeholder without data", () => {
    render(<OutingsCard petName="Haru" rangeLabel="30d" />);
    expect(screen.getByRole("note")).toHaveTextContent(/walks will appear/i);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("frames the headline count as a floor", () => {
    render(<OutingsCard petName="Haru" data={makeData()} />);
    expect(screen.getByText("≥ 3")).toBeInTheDocument();
    expect(screen.getByText(/counts are a floor/i)).toBeInTheDocument();
  });

  it("lists each outing with floor-framed duration and distance", () => {
    render(<OutingsCard petName="Haru" data={makeData()} />);
    expect(screen.getByText("07:40")).toBeInTheDocument();
    expect(screen.getByText("at least 32 min")).toBeInTheDocument();
    expect(screen.getByText("up to 0.8 km away")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("explains that a zero-outing day is not proof the dog stayed in", () => {
    render(
      <OutingsCard
        petName="Haru"
        data={makeData({ latestCount: 0, latestRows: [] })}
      />,
    );
    expect(screen.getByText(/not proof Haru stayed in/i)).toBeInTheDocument();
  });

  it("shows the range average with the truncated-duration caveat", () => {
    render(<OutingsCard petName="Haru" data={makeData()} />);
    expect(
      screen.getByText(/at least 2\.8 outings per day on average across 25 days/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/real walks run longer/i)).toBeInTheDocument();
  });

  it("omits the range average for a single-day range", () => {
    render(
      <OutingsCard petName="Haru" data={makeData({ rangeDailyAverage: null })} />,
    );
    expect(screen.queryByText(/per day on average/i)).not.toBeInTheDocument();
  });
});
