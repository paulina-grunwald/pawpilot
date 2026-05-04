import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { HowItWorks } from "./HowItWorks";

describe("HowItWorks", () => {
  it("renders all three numbered steps", () => {
    render(<HowItWorks />);
    expect(screen.getByText("01")).toBeInTheDocument();
    expect(screen.getByText("02")).toBeInTheDocument();
    expect(screen.getByText("03")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /pair the collar/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /build haru's normal/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /ask, or get pinged/i })).toBeInTheDocument();
  });
});
