import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { PetDetailView, type PetDetailData } from "./PetDetailView";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

const samplePet: PetDetailData = {
  id: "pet-uuid",
  name: "Luna",
  breed: "Australian Shepherd",
  sexDisplay: "Female",
  spayedNeuteredDisplay: "Spayed",
  lifeStage: "Adult",
  ageDisplay: "4 yrs",
  birthdayDisplay: "Jun 14, 2021",
  weightDisplay: "22.0 kg",
  notes: "Loves frisbee.",
};

describe("PetDetailView", () => {
  it("renders the pet name, breed, and life-stage chip", () => {
    render(<PetDetailView pet={samplePet} />);
    expect(screen.getByRole("heading", { name: "Luna", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("Australian Shepherd")).toBeInTheDocument();
    expect(screen.getByText("Adult")).toBeInTheDocument();
  });

  it("renders all four fact stats with their labels", () => {
    render(<PetDetailView pet={samplePet} />);
    expect(screen.getByText(/^age$/i)).toBeInTheDocument();
    expect(screen.getByText("4 yrs")).toBeInTheDocument();
    expect(screen.getByText(/birthday/i)).toBeInTheDocument();
    expect(screen.getByText("Jun 14, 2021")).toBeInTheDocument();
    expect(screen.getByText("22.0 kg")).toBeInTheDocument();
    expect(screen.getByText(/female · spayed/i)).toBeInTheDocument();
  });

  it("renders the notes content when present", () => {
    render(<PetDetailView pet={samplePet} />);
    expect(screen.getByText("Loves frisbee.")).toBeInTheDocument();
  });

  it("renders a 'No notes yet.' placeholder when notes is empty", () => {
    render(<PetDetailView pet={{ ...samplePet, notes: "" }} />);
    expect(screen.getByText(/no notes yet/i)).toBeInTheDocument();
  });

  it("renders an edit-notes link pointing at the edit page", () => {
    render(<PetDetailView pet={samplePet} />);
    const link = screen.getByRole("link", { name: /edit notes/i });
    expect(link).toHaveAttribute("href", "/pets/pet-uuid/edit");
  });

  it("renders the Tractive upload control in the Wearable card", () => {
    render(<PetDetailView pet={samplePet} />);
    expect(screen.getByRole("button", { name: /upload export/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/tractive export zip/i)).toBeInTheDocument();
  });
});
