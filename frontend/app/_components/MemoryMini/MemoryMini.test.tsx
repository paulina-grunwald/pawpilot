import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MemoryMini } from "./MemoryMini";

describe("MemoryMini", () => {
  it("renders each memory item with its date and text", () => {
    render(<MemoryMini />);
    expect(screen.getByText("Mar 2024")).toBeInTheDocument();
    expect(screen.getByText(/Hip dysplasia/i)).toBeInTheDocument();
    expect(screen.getByText("Now")).toBeInTheDocument();
    expect(screen.getByText(/Activity ↓ 38%/)).toBeInTheDocument();
  });
});
