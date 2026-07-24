import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatTile } from "./StatTile";

describe("StatTile", () => {
  it("renders the label, value, unit, and delta", () => {
    render(<StatTile label="Active" value="58" unit="min" delta="+12 vs avg" tone="positive" />);
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("58")).toBeInTheDocument();
    expect(screen.getByText("min")).toBeInTheDocument();
    expect(screen.getByText("+12 vs avg")).toBeInTheDocument();
  });

  it("renders an em-dash and 'Awaiting data' when placeholder is true", () => {
    render(<StatTile label="Resting HR" value="68" unit="bpm" placeholder />);
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.getByText(/awaiting data/i)).toBeInTheDocument();
    expect(screen.queryByText("bpm")).not.toBeInTheDocument();
    expect(screen.queryByText("68")).not.toBeInTheDocument();
  });

  it("omits the unit when none is provided", () => {
    render(<StatTile label="Rest" value="6h 12m" />);
    expect(screen.getByText("6h 12m")).toBeInTheDocument();
  });

  it("omits the delta line when delta is not provided and not placeholder", () => {
    const { container } = render(<StatTile label="Rest" value="6h 12m" />);
    expect(container.querySelectorAll("p").length).toBe(1);
  });
});
