import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { HeroDashboardCard } from "./HeroDashboardCard";

describe("HeroDashboardCard", () => {
  it("renders Haru's identity, alert copy and a sparkline svg with gradient", () => {
    const { container } = render(<HeroDashboardCard />);
    expect(screen.getByText(/Haru/)).toBeInTheDocument();
    expect(screen.getByText(/AUSTRALIAN SHEPHERD · 6Y/)).toBeInTheDocument();
    expect(screen.getByText(/Activity ↓ 38%/)).toBeInTheDocument();
    expect(container.querySelector("#hero-spark-fill")).toBeInTheDocument();
  });
});
