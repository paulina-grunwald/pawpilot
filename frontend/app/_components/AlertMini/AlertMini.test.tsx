import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { AlertMini } from "./AlertMini";

describe("AlertMini", () => {
  it("renders all alert rows", () => {
    render(<AlertMini />);
    expect(screen.getByText("TUE")).toBeInTheDocument();
    expect(screen.getByText("WED")).toBeInTheDocument();
    expect(screen.getByText("THU")).toBeInTheDocument();
  });

  it("highlights the strong alert with a bell icon", () => {
    const { container } = render(<AlertMini />);
    const svgs = container.querySelectorAll("svg");
    expect(svgs.length).toBe(1);
    expect(svgs[0].getAttribute("stroke")).toBe("var(--ochre)");
  });
});
