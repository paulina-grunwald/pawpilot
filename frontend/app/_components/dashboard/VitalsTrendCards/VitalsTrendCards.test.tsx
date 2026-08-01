import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { VitalsTrendsData, VitalTrendSeries } from "@/lib/tractive.format";
import { VitalsTrendCards } from "./VitalsTrendCards";

function makeSeries(overrides: Partial<VitalTrendSeries> = {}): VitalTrendSeries {
  return {
    values: [62, 64, 61, 66, 65],
    days: ["Mo", "Tu", "We", "Th", "Fr"],
    dates: ["May 12", "May 13", "May 14", "May 15", "May 16"],
    latest: 65,
    typicalRange: { low: 62, high: 65 },
    measuredDayCount: 5,
    suppressedDayCount: 0,
    ...overrides,
  };
}

function makeData(overrides: Partial<VitalsTrendsData> = {}): VitalsTrendsData {
  return {
    heartRate: makeSeries(),
    respiratoryRate: makeSeries({ values: [17, 18, 16, 19, 18], latest: 18 }),
    ...overrides,
  };
}

describe("VitalsTrendCards", () => {
  it("renders connect placeholders when no data is provided", () => {
    render(<VitalsTrendCards petName="Haru" />);
    const notes = screen.getAllByText(/vitals will appear once tractive is connected/i);
    expect(notes).toHaveLength(2);
  });

  it("renders both charts with accessible labels and latest headlines", () => {
    render(<VitalsTrendCards petName="Haru" data={makeData()} rangeLabel="30d" />);
    expect(
      screen.getByRole("img", { name: "Resting heart rate over the past 30d" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Resting respiratory rate over the past 30d" }),
    ).toBeInTheDocument();
    const headlineValues = screen
      .getAllByText(/^(65|18)$/)
      .filter((element) => element.classList.contains("display"));
    expect(headlineValues).toHaveLength(2);
  });

  it("labels the band as the dog's own typical range, never clinical", () => {
    render(<VitalsTrendCards petName="Haru" data={makeData()} />);
    expect(screen.getAllByText("typical for Haru").length).toBeGreaterThan(0);
    expect(
      screen.getAllByText(/own typical range, not a clinical one/i).length,
    ).toBeGreaterThan(0);
    expect(screen.queryByText(/normal range/i)).not.toBeInTheDocument();
  });

  it("notes suppressed low-reading days", () => {
    render(
      <VitalsTrendCards
        petName="Haru"
        data={makeData({ heartRate: makeSeries({ suppressedDayCount: 2 }) })}
      />,
    );
    expect(screen.getByText(/2 days with too few readings not plotted/i)).toBeInTheDocument();
  });

  it("shows the night vs day respiratory callout when available", () => {
    render(
      <VitalsTrendCards
        petName="Haru"
        data={makeData({
          respiratoryNightDay: {
            nightMean: 16.5,
            dayMean: 22,
            nightRecordCount: 40,
            dayRecordCount: 20,
          },
        })}
      />,
    );
    expect(
      screen.getByText(/night 16\.5\/min vs day 22\/min · from 60 resting readings/i),
    ).toBeInTheDocument();
  });

  it("stays descriptive when night is higher than day", () => {
    render(
      <VitalsTrendCards
        petName="Haru"
        data={makeData({
          respiratoryNightDay: {
            nightMean: 24,
            dayMean: 18,
            nightRecordCount: 30,
            dayRecordCount: 30,
          },
        })}
      />,
    );
    expect(screen.getByText(/night 24\/min vs day 18\/min/i)).toBeInTheDocument();
    expect(screen.queryByText(/healthy/i)).not.toBeInTheDocument();
  });

  it("never renders evaluative health claims in the callout", () => {
    render(<VitalsTrendCards petName="Haru" data={makeData()} />);
    expect(screen.queryByText(/healthy/i)).not.toBeInTheDocument();
  });

  it("omits the night vs day callout when not provided", () => {
    render(<VitalsTrendCards petName="Haru" data={makeData()} />);
    expect(screen.queryByText(/vs day/i)).not.toBeInTheDocument();
  });

  it("omits the shaded-band footnote when the chart has no typical band", () => {
    render(
      <VitalsTrendCards
        petName="Haru"
        data={makeData({
          heartRate: makeSeries({
            values: [62, 64, 61],
            days: ["Mo", "Tu", "We"],
            dates: ["May 12", "May 13", "May 14"],
            latest: 61,
            typicalRange: undefined,
          }),
          respiratoryRate: makeSeries({
            values: [17, 18, 16],
            days: ["Mo", "Tu", "We"],
            dates: ["May 12", "May 13", "May 14"],
            latest: 16,
            typicalRange: undefined,
          }),
        })}
      />,
    );
    expect(screen.queryByText(/shaded band/i)).not.toBeInTheDocument();
  });

  it("discloses suppressed days without claiming a band that is not drawn", () => {
    render(
      <VitalsTrendCards
        petName="Haru"
        data={makeData({
          heartRate: makeSeries({
            values: [62, 64],
            days: ["Mo", "Tu"],
            dates: ["May 12", "May 13"],
            latest: 64,
            typicalRange: undefined,
            suppressedDayCount: 3,
          }),
        })}
      />,
    );
    expect(screen.getByText(/3 days with too few readings not plotted/i)).toBeInTheDocument();
    const suppressionNote = screen.getByText(/3 days with too few readings not plotted/i);
    expect(suppressionNote.textContent).not.toMatch(/shaded band/i);
  });

  it("shows the latest reading's date next to the headline", () => {
    render(<VitalsTrendCards petName="Haru" data={makeData()} />);
    expect(screen.getAllByText("as of May 16").length).toBeGreaterThan(0);
  });

  it("shows the not-enough-readings placeholder for a loaded but sparse range", () => {
    render(
      <VitalsTrendCards
        petName="Haru"
        data={makeData({
          heartRate: makeSeries({
            values: [62],
            days: ["Mo"],
            dates: ["May 12"],
            latest: 62,
            typicalRange: undefined,
            measuredDayCount: 3,
            suppressedDayCount: 2,
          }),
        })}
      />,
    );
    expect(
      screen.getByText(/not enough resting readings in this range to chart honestly/i),
    ).toBeInTheDocument();
  });
});
