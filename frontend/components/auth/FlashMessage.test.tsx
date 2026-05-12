import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { FlashMessage } from "./FlashMessage";

describe("FlashMessage", () => {
  it("renders nothing when flashKey is null", () => {
    const { container } = render(<FlashMessage flashKey={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when flashKey is undefined", () => {
    const { container } = render(<FlashMessage flashKey={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing for an unknown flashKey", () => {
    const { container } = render(<FlashMessage flashKey="not-a-real-key" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the mapped copy for 'password-reset-success'", () => {
    render(<FlashMessage flashKey="password-reset-success" />);
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent(/password updated — please log in\./i);
  });
});
