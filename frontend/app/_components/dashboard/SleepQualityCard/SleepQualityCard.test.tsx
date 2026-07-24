import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { SleepQualityData } from "@/lib/tractive.format";
import { SleepQualityCard } from "./SleepQualityCard";

function makeData(overrides: Partial<SleepQualityData> = {}): SleepQualityData {
  return {
    values: [375, 420, 301, 455, 340],
    days: ["Mo", "Tu", "We", "Th", "Fr"],
    dates: ["May 12", "May 13", "May 14", "May 15", "May 16"],
    latestLongestBoutMinutes: 340,
    averageBoutCount: 7.7,
    averageFragmentationIndex: 9.8,
    lowCoverageDayCount: 0,
    ...overrides,
  };
}

describe("SleepQualityCard", () => {
  it("renders the connect placeholder without data", () => {
    render(<SleepQualityCard petName="Haru" />);
    expect(screen.getByRole("note")).toHaveTextContent(/sleep continuity will appear/i);
  });

  it("renders the chart with an hours-minutes headline", () => {
    render(<SleepQualityCard petName="Haru" data={makeData()} rangeLabel="30d" />);
    const headline = screen
      .getAllByText("5h 40m")
      .filter((element) => element.classList.contains("display"));
    expect(headline).toHaveLength(1);
    expect(
      screen.getByRole("img", {
        name: /longest unbroken rest stretch per day over the past 30d/i,
      }),
    ).toBeInTheDocument();
  });

  it("explains continuity without claiming sleep stages", () => {
    render(<SleepQualityCard petName="Haru" data={makeData()} />);
    expect(
      screen.getByText(/not deep or light sleep, which this tracker cannot see/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/7\.7 rest stretches per day/i)).toBeInTheDocument();
    expect(screen.getByText(/9\.8 brief wake-ups per hour of rest/i)).toBeInTheDocument();
  });

  it("caveats low-coverage days", () => {
    render(
      <SleepQualityCard petName="Haru" data={makeData({ lowCoverageDayCount: 3 })} />,
    );
    expect(screen.getByText(/3 days with missing data understate rest/i)).toBeInTheDocument();
  });

  it("omits the low-coverage caveat when every day is clean", () => {
    render(<SleepQualityCard petName="Haru" data={makeData()} />);
    expect(screen.queryByText(/understate rest/i)).not.toBeInTheDocument();
  });

  it("shows the sparse placeholder for a single-day range", () => {
    render(
      <SleepQualityCard
        petName="Haru"
        data={makeData({ values: [375], days: ["Mo"], dates: ["May 12"] })}
      />,
    );
    expect(screen.getByText(/not enough days in this range/i)).toBeInTheDocument();
  });
});

describe("SleepQualityCard footnote combinations", () => {
  it("reads cleanly when fragmentation is unavailable", () => {
    render(
      <SleepQualityCard
        petName="Haru"
        data={makeData({ averageFragmentationIndex: null })}
      />,
    );
    expect(
      screen.getByText(/averages 7\.7 rest stretches per day\s*\. these describe/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/wake-ups per hour/i)).not.toBeInTheDocument();
  });

  it("uses singular wording for one low-coverage day", () => {
    render(
      <SleepQualityCard petName="Haru" data={makeData({ lowCoverageDayCount: 1 })} />,
    );
    expect(screen.getByText(/1 day with missing data understate/i)).toBeInTheDocument();
  });
});
