import { render, screen, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Nav } from "./Nav";

describe("Nav", () => {
  it("renders home link, section anchors and the login CTA", () => {
    render(<Nav />);
    expect(screen.getByLabelText(/PawPilot — home/i)).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: /how it works/i })).toHaveAttribute("href", "#how");
    expect(screen.getByRole("link", { name: /why pawpilot/i })).toHaveAttribute("href", "#why");
    expect(screen.getByRole("link", { name: /the science/i })).toHaveAttribute("href", "#trust");
    expect(screen.getByRole("link", { name: /log in/i })).toHaveAttribute("href", "/login");
  });

  it("toggles the scrolled background after scrolling past 24px", () => {
    const { container } = render(<Nav />);
    const header = container.querySelector("header")!;
    expect(header.style.background).toBe("transparent");

    act(() => {
      Object.defineProperty(window, "scrollY", { value: 100, writable: true, configurable: true });
      window.dispatchEvent(new Event("scroll"));
    });

    expect(header.style.background).toContain("color-mix");
    expect(header.style.background).toContain("var(--paper)");
  });
});
