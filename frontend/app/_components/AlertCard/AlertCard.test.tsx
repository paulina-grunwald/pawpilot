import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { AlertCard } from "./AlertCard";

describe("AlertCard", () => {
  it("renders the alert summary, action buttons and a sparkline svg", () => {
    const { container } = render(<AlertCard />);

    expect(screen.getByText(/heads up · 7:42 am/i)).toBeInTheDocument();
    expect(screen.getByText(/Haru · 6yr Aussie/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ask pawpilot/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /snooze/i })).toBeInTheDocument();

    expect(container.querySelector("#alert-card-spark-fill")).toBeInTheDocument();
  });
});
