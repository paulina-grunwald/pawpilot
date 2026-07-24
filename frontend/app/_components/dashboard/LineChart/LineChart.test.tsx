import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { LineChart } from "./LineChart";

describe("LineChart", () => {
  it("renders nothing visible when fewer than 2 values are provided", () => {
    const { container } = render(<LineChart values={[5]} />);
    expect(container.querySelector("svg")).toBeNull();
  });

  it("renders an SVG with the accessible label when given values", () => {
    render(
      <LineChart values={[10, 12, 8, 15, 18, 22, 24]} accessibleLabel="Activity, past 7 days" />,
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
});
