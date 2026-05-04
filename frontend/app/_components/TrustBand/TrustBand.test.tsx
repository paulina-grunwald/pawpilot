import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { TrustBand } from "./TrustBand";

describe("TrustBand", () => {
  it("renders the section copy and pill labels", () => {
    render(<TrustBand />);
    expect(screen.getByRole("heading", { name: /not your vet/i })).toBeInTheDocument();
    expect(screen.getByText(/Cited answers/)).toBeInTheDocument();
    expect(screen.getByText(/Urgency-classified/)).toBeInTheDocument();
    expect(screen.getByText(/Vet-reviewed corpus/)).toBeInTheDocument();
  });

  it("references images that exist in /public/img/", () => {
    const { container } = render(<TrustBand />);
    const images = container.querySelectorAll("img");
    const sources = Array.from(images).map((image) => image.getAttribute("src") ?? "");
    expect(sources.some((source) => source.includes("aussie-running"))).toBe(true);
    expect(sources.some((source) => source.includes("owner-and-dog"))).toBe(true);
  });
});
