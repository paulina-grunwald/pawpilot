import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Differentiators } from "./Differentiators";

describe("Differentiators", () => {
  it("renders all four cards with their headings", () => {
    render(<Differentiators />);
    expect(screen.getByRole("heading", { name: /speaks fluent tractive/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /notices before you do/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /two minds, no echo chamber/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /haru's whole story/i })).toBeInTheDocument();
  });

  it("includes the section eyebrow numbers", () => {
    render(<Differentiators />);
    expect(screen.getByText("01")).toBeInTheDocument();
    expect(screen.getByText("02")).toBeInTheDocument();
    expect(screen.getByText("03")).toBeInTheDocument();
    expect(screen.getByText("04")).toBeInTheDocument();
  });
});
