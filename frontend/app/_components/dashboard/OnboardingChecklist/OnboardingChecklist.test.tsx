import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { OnboardingChecklist } from "./OnboardingChecklist";

describe("OnboardingChecklist", () => {
  it("renders all four steps with the user's email in step 1", () => {
    render(<OnboardingChecklist userEmail="alice@example.com" />);
    expect(screen.getByText(/signed in as alice@example.com/i)).toBeInTheDocument();
    expect(screen.getByText(/add your first dog/i)).toBeInTheDocument();
    expect(screen.getByText(/connect your tractive collar/i)).toBeInTheDocument();
    expect(screen.getByText(/ask your first question/i)).toBeInTheDocument();
  });

  it("marks step 1 as complete via the badge image label", () => {
    render(<OnboardingChecklist userEmail="alice@example.com" />);
    expect(screen.getByRole("img", { name: /step 1: complete/i })).toBeInTheDocument();
  });

  it("renders the 'Add pet' CTA pointing at /pets/new on step 2", () => {
    render(<OnboardingChecklist userEmail="alice@example.com" />);
    const cta = screen.getByRole("link", { name: /add pet/i });
    expect(cta).toHaveAttribute("href", "/pets/new");
  });

  it("renders only one CTA — the later steps are inactive until earlier ones complete", () => {
    render(<OnboardingChecklist userEmail="alice@example.com" />);
    expect(screen.getAllByRole("link")).toHaveLength(1);
  });
});
