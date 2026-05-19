import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AuthCard } from "./AuthCard";

describe("AuthCard", () => {
  it("renders title, subtitle, children, and footer", () => {
    render(
      <AuthCard
        title="Welcome back"
        subtitle="Log in to keep tabs on your pup"
        footer={<span>footer content</span>}
      >
        <p>form goes here</p>
      </AuthCard>,
    );
    expect(screen.getByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    expect(screen.getByText("Log in to keep tabs on your pup")).toBeInTheDocument();
    expect(screen.getByText("form goes here")).toBeInTheDocument();
    expect(screen.getByText("footer content")).toBeInTheDocument();
  });

  it("renders the PawPilot home link", () => {
    render(
      <AuthCard title="Title">
        <span />
      </AuthCard>,
    );
    expect(screen.getByLabelText("PawPilot — home")).toHaveAttribute("href", "/");
  });

  it("omits subtitle and footer when not provided", () => {
    render(
      <AuthCard title="Title">
        <span />
      </AuthCard>,
    );
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });
});
