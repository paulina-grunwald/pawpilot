import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PetCard, type PetCardData } from "./PetCard";

const samplePet: PetCardData = {
  id: "pet-uuid",
  name: "Luna",
  breed: "Australian Shepherd",
  ageDisplay: "4 yrs",
  weightDisplay: "22.0 kg",
  sexDisplay: "spayed female",
  lifeStage: "Adult",
  photoUrl: null,
};

describe("PetCard", () => {
  it("renders pet name, breed line, and life-stage chip", () => {
    render(<PetCard pet={samplePet} />);
    expect(screen.getByRole("heading", { name: "Luna" })).toBeInTheDocument();
    expect(
      screen.getByText(/Australian Shepherd · 4 yrs · 22\.0 kg · spayed female/i),
    ).toBeInTheDocument();
    expect(screen.getByText("Adult")).toBeInTheDocument();
  });

  it("links to /pets/{id} by default", () => {
    render(<PetCard pet={samplePet} />);
    const link = screen.getByRole("link", { name: /open luna's profile/i });
    expect(link).toHaveAttribute("href", "/pets/pet-uuid");
  });

  it("uses a custom href when provided", () => {
    render(<PetCard pet={samplePet} href="/dev/inspect" />);
    expect(screen.getByRole("link", { name: /open luna's profile/i })).toHaveAttribute(
      "href",
      "/dev/inspect",
    );
  });

  it("renders initials placeholder when no photo URL", () => {
    render(<PetCard pet={{ ...samplePet, name: "Luna Dog" }} />);
    expect(screen.getByText("LD")).toBeInTheDocument();
  });

  it("renders the photo image when photoUrl is provided", () => {
    render(<PetCard pet={{ ...samplePet, photoUrl: "https://media/luna.jpg" }} />);
    const image = screen.getByRole("img", { name: /luna's photo/i });
    expect(image).toHaveAttribute("src", "https://media/luna.jpg");
  });
});
