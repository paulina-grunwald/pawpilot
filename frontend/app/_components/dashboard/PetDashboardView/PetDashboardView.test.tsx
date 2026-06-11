import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PetDashboardView } from "./PetDashboardView";

const samplePet = {
  id: "pet-1",
  name: "Luna",
  breed: "Aussie mix",
  ageDisplay: "4 yrs",
  weightDisplay: "22.0 kg",
  sexDisplay: "spayed female",
  lifeStage: "Adult",
  photoUrl: null,
};

describe("PetDashboardView", () => {
  it("renders the pet name and today label", () => {
    render(<PetDashboardView pet={samplePet} todayLabel="Sat, May 23" />);
    expect(screen.getByRole("heading", { name: "Luna" })).toBeInTheDocument();
    expect(screen.getByText(/sat, may 23/i)).toBeInTheDocument();
  });

  it("renders headerActions when provided", () => {
    render(
      <PetDashboardView
        pet={samplePet}
        todayLabel="Sat, May 23"
        headerActions={<button type="button">Switch</button>}
      />,
    );
    expect(screen.getByRole("button", { name: /switch/i })).toBeInTheDocument();
  });

  it("does not render an actions wrapper when headerActions is undefined", () => {
    const { container } = render(<PetDashboardView pet={samplePet} todayLabel="Sat, May 23" />);
    expect(container.querySelector("button")).toBeNull();
  });
});
