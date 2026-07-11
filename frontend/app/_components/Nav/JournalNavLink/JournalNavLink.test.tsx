import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { activePetStorageKey } from "@/lib/activePet";
import { JournalNavLink } from "./JournalNavLink";

const { pathnameMock } = vi.hoisted(() => ({
  pathnameMock: vi.fn<() => string>(() => "/dashboard"),
}));

vi.mock("next/navigation", () => ({ usePathname: () => pathnameMock() }));

const USER_ID = "user-uuid";

afterEach(() => {
  pathnameMock.mockReturnValue("/dashboard");
  window.localStorage.clear();
});

function journalLinkHref(): string | null {
  return screen.getByRole("link", { name: "Journal" }).getAttribute("href");
}

describe("JournalNavLink", () => {
  it("targets the pet in a /dashboard/[petId] route", () => {
    pathnameMock.mockReturnValue("/dashboard/pet-9");
    render(<JournalNavLink userId={USER_ID} />);
    expect(journalLinkHref()).toBe("/pets/pet-9/journal");
  });

  it("targets the pet in a /pets/[petId] route", () => {
    pathnameMock.mockReturnValue("/pets/pet-3/edit");
    render(<JournalNavLink userId={USER_ID} />);
    expect(journalLinkHref()).toBe("/pets/pet-3/journal");
  });

  it("falls back to the stored active pet on a non-pet route", () => {
    window.localStorage.setItem(activePetStorageKey(USER_ID), "pet-7");
    pathnameMock.mockReturnValue("/pets/new");
    render(<JournalNavLink userId={USER_ID} />);
    expect(journalLinkHref()).toBe("/pets/pet-7/journal");
  });

  it("points at /dashboard when no pet is known", () => {
    pathnameMock.mockReturnValue("/chat");
    render(<JournalNavLink userId={USER_ID} />);
    expect(journalLinkHref()).toBe("/dashboard");
  });

  it("applies the provided className", () => {
    pathnameMock.mockReturnValue("/dashboard/pet-1");
    render(<JournalNavLink userId={USER_ID} className="nav-link" />);
    expect(screen.getByRole("link", { name: "Journal" })).toHaveClass("nav-link");
  });
});
