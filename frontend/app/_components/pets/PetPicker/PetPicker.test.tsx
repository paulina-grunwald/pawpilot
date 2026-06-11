import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PetPicker, type PetPickerOption } from "./PetPicker";

const pets: PetPickerOption[] = [
  { id: "pet-1", name: "Luna", breed: "Australian Shepherd" },
  { id: "pet-2", name: "Bowie", breed: "Border Collie" },
];

describe("PetPicker", () => {
  it("shows the active pet name on the trigger", () => {
    render(<PetPicker pets={pets} activePetId="pet-2" onSelect={() => {}} />);
    expect(screen.getByRole("button", { name: /bowie/i })).toBeInTheDocument();
  });

  it("opens the listbox when clicked and lists all pets", async () => {
    const user = userEvent.setup();
    render(<PetPicker pets={pets} activePetId="pet-1" onSelect={() => {}} />);
    await user.click(screen.getByRole("button", { name: /luna/i }));
    const listbox = screen.getByRole("listbox", { name: /switch active pet/i });
    expect(listbox).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /luna/i })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("option", { name: /bowie/i })).toHaveAttribute(
      "aria-selected",
      "false",
    );
  });

  it("calls onSelect with the chosen pet id and closes the menu", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<PetPicker pets={pets} activePetId="pet-1" onSelect={onSelect} />);
    await user.click(screen.getByRole("button", { name: /luna/i }));
    await user.click(screen.getByRole("option", { name: /bowie/i }));
    expect(onSelect).toHaveBeenCalledWith("pet-2");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("renders an 'Add another dog' link to /pets/new", async () => {
    const user = userEvent.setup();
    render(<PetPicker pets={pets} activePetId="pet-1" onSelect={() => {}} />);
    await user.click(screen.getByRole("button", { name: /luna/i }));
    expect(screen.getByRole("link", { name: /add another dog/i })).toHaveAttribute(
      "href",
      "/pets/new",
    );
  });

  it("closes on Escape and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    render(<PetPicker pets={pets} activePetId="pet-1" onSelect={() => {}} />);
    const trigger = screen.getByRole("button", { name: /luna/i });
    await user.click(trigger);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
