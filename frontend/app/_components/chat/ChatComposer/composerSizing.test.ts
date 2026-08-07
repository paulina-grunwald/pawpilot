import { describe, expect, it } from "vitest";
import { COMPOSER_MAX_HEIGHT, resolveComposerSizing } from "./composerSizing";

describe("resolveComposerSizing", () => {
  it("grows to fit content below the cap and hides the scrollbar", () => {
    expect(resolveComposerSizing(72, 160)).toEqual({ height: 72, overflowY: "hidden" });
  });

  it("clamps to the cap and scrolls once content exceeds it", () => {
    expect(resolveComposerSizing(400, 160)).toEqual({ height: 160, overflowY: "auto" });
  });

  it("scrolls at exactly the cap", () => {
    expect(resolveComposerSizing(160, 160)).toEqual({ height: 160, overflowY: "auto" });
  });

  it("never returns a negative height", () => {
    expect(resolveComposerSizing(-20, 160)).toEqual({ height: 0, overflowY: "hidden" });
  });

  it("defaults to the shared composer cap", () => {
    expect(resolveComposerSizing(9999)).toEqual({
      height: COMPOSER_MAX_HEIGHT,
      overflowY: "auto",
    });
  });
});
