import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PetActions } from "./PetActions";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }),
}));

describe("PetActions", () => {
  it("renders the Edit link pointing at the edit route", () => {
    render(<PetActions petId="pet-1" petName="Luna" />);
    const editLink = screen.getByRole("link", { name: /edit luna/i });
    expect(editLink).toHaveAttribute("href", "/pets/pet-1/edit");
  });

  it("opens the delete confirmation dialog on Delete click", async () => {
    const user = userEvent.setup();
    render(<PetActions petId="pet-1" petName="Luna" />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^delete$/i }));
    expect(screen.getByRole("dialog", { name: /delete luna/i })).toBeInTheDocument();
  });
});
