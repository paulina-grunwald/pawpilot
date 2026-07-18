import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { IntradayActivityMatrix } from "@/lib/tractive.format";
import { IntradayActivityCard } from "./IntradayActivityCard";

function makeMatrix(): IntradayActivityMatrix {
  const quietDay = Array.from({ length: 24 }, () => 0);
  const busyDay = Array.from({ length: 24 }, (_, hour) => (hour === 8 ? 40 : 2));
  return {
    rows: [
      {
        date: "2024-05-15",
        dayLabel: "May 15",
        hourlyActiveMinutes: busyDay,
        lowCoverage: false,
      },
      {
        date: "2024-05-16",
        dayLabel: "May 16",
        hourlyActiveMinutes: quietDay,
        lowCoverage: true,
      },
    ],
    maxActiveMinutes: 40,
  };
}

describe("IntradayActivityCard", () => {
  it("renders the placeholder when no matrix is provided", () => {
    render(<IntradayActivityCard petName="Haru" />);
    expect(screen.getByRole("note")).toHaveTextContent(/hour-by-hour activity/i);
  });

  it("renders the placeholder when the matrix has no rows", () => {
    render(
      <IntradayActivityCard petName="Haru" matrix={{ rows: [], maxActiveMinutes: 0 }} />,
    );
    expect(screen.getByRole("note")).toHaveTextContent(/hour-by-hour activity/i);
  });

  it("renders 24 cells per day with per-cell tooltips", () => {
    const { container } = render(
      <IntradayActivityCard petName="Haru" matrix={makeMatrix()} />,
    );
    const cells = container.querySelectorAll("span[title]");
    expect(cells).toHaveLength(48);
    expect(cells[8].getAttribute("title")).toBe("May 15 08:00 · 40 min active");
  });

  it("names the grid for assistive tech with the pet and day count", () => {
    render(<IntradayActivityCard petName="Haru" matrix={makeMatrix()} />);
    expect(
      screen.getByRole("img", { name: "Active minutes per hour across 2 days for Haru" }),
    ).toBeInTheDocument();
  });

  it("marks low-coverage days and explains the marker in the legend", () => {
    render(<IntradayActivityCard petName="Haru" matrix={makeMatrix()} />);
    expect(screen.getByText("May 16*")).toBeInTheDocument();
    expect(screen.getByText(/totals are a floor/i)).toBeInTheDocument();
  });

  it("omits the low-coverage legend line when every day is clean", () => {
    const matrix = makeMatrix();
    const cleanMatrix = {
      ...matrix,
      rows: matrix.rows.map((row) => ({ ...row, lowCoverage: false })),
    };
    render(<IntradayActivityCard petName="Haru" matrix={cleanMatrix} />);
    expect(screen.queryByText(/totals are a floor/i)).not.toBeInTheDocument();
  });

  it("shows the range label in the subtitle", () => {
    render(
      <IntradayActivityCard petName="Haru" matrix={makeMatrix()} rangeLabel="30d" />,
    );
    expect(screen.getByText(/past 30d/i)).toBeInTheDocument();
  });
});

describe("IntradayActivityCard long ranges and empty activity", () => {
  it("thins day labels for ranges longer than 14 days but keeps the last", () => {
    const rows = Array.from({ length: 30 }, (_, index) => ({
      date: `2024-04-${String(index + 1).padStart(2, "0")}`,
      dayLabel: `Apr ${index + 1}`,
      hourlyActiveMinutes: Array.from({ length: 24 }, () => 1),
      lowCoverage: false,
    }));
    render(
      <IntradayActivityCard petName="Haru" matrix={{ rows, maxActiveMinutes: 1 }} />,
    );
    expect(screen.getByText("Apr 1")).toBeInTheDocument();
    expect(screen.getByText("Apr 30")).toBeInTheDocument();
    expect(screen.queryByText("Apr 2")).not.toBeInTheDocument();
  });

  it("renders without crashing when the whole range has zero activity", () => {
    const quietRow = {
      date: "2024-05-15",
      dayLabel: "May 15",
      hourlyActiveMinutes: Array.from({ length: 24 }, () => 0),
      lowCoverage: false,
    };
    const { container } = render(
      <IntradayActivityCard
        petName="Haru"
        matrix={{ rows: [quietRow], maxActiveMinutes: 0 }}
      />,
    );
    expect(container.querySelectorAll("span[title]")).toHaveLength(24);
  });
});
