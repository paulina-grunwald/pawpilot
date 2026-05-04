import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { PhoneMock } from "./PhoneMock";

describe("PhoneMock", () => {
  it("renders the device chrome and embedded AlertCard", () => {
    const { container } = render(<PhoneMock />);
    expect(container.querySelector("svg")).toBeInTheDocument();
    expect(container.textContent).toContain("9:41");
    expect(container.textContent).toContain("Tuesday");
    expect(container.textContent).toContain("Haru's a little off");
  });
});
