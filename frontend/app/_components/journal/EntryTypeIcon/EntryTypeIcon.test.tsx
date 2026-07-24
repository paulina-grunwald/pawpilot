import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { ENTRY_TYPES } from "@/lib/journal.constants";
import { EntryTypeIcon, SearchIcon } from "./EntryTypeIcon";

describe("EntryTypeIcon", () => {
  it("renders a decorative svg for every entry type", () => {
    for (const entryType of ENTRY_TYPES) {
      const { container } = render(<EntryTypeIcon type={entryType} />);
      const svg = container.querySelector("svg");
      expect(svg).not.toBeNull();
      expect(svg).toHaveAttribute("aria-hidden", "true");
    }
  });

  it("honors the size prop", () => {
    const { container } = render(<EntryTypeIcon type="meal" size={24} />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("width", "24");
    expect(svg).toHaveAttribute("height", "24");
  });

  it("renders the search glyph", () => {
    const { container } = render(<SearchIcon />);
    expect(container.querySelector("svg")).not.toBeNull();
  });
});
