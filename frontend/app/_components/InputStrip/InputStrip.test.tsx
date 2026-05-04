import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { InputStrip } from "./InputStrip";

describe("InputStrip", () => {
  it("renders the four input-type tiles", () => {
    render(<InputStrip />);
    expect(screen.getByText(/A photo/)).toBeInTheDocument();
    expect(screen.getByText(/Ten seconds of video/)).toBeInTheDocument();
    expect(screen.getByText(/A bloodwork PDF/)).toBeInTheDocument();
    expect(screen.getByText(/Just text/)).toBeInTheDocument();
  });
});
