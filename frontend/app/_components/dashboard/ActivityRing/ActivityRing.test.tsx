import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ActivityRing } from "./ActivityRing";

describe("ActivityRing", () => {
  it("uses the provided accessibleLabel as aria-label", () => {
    render(
      <ActivityRing percent={45} label="45%" sublabel="of goal" accessibleLabel="Daily activity 45%" />,
    );
    expect(screen.getByRole("img", { name: /daily activity 45%/i })).toBeInTheDocument();
  });

  it("falls back to label + sublabel for aria-label when no accessibleLabel is given", () => {
    render(<ActivityRing percent={20} label="20%" sublabel="of daily goal" />);
    expect(screen.getByRole("img", { name: /20% of daily goal/i })).toBeInTheDocument();
  });

  it("renders the label text in the center", () => {
    render(<ActivityRing percent={78} label="78%" sublabel="of daily goal" />);
    expect(screen.getByText("78%")).toBeInTheDocument();
    expect(screen.getByText("of daily goal")).toBeInTheDocument();
  });
});
