import { describe, expect, it } from "vitest";
import { renderHook } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { useIsHydrated } from "./useIsHydrated";

function HydrationProbe() {
  return <span>{useIsHydrated() ? "hydrated" : "not-hydrated"}</span>;
}

describe("useIsHydrated", () => {
  it("returns false during server rendering", () => {
    expect(renderToString(<HydrationProbe />)).toContain("not-hydrated");
  });

  it("returns true once the mount effect has run on the client", () => {
    const { result } = renderHook(() => useIsHydrated());
    expect(result.current).toBe(true);
  });

  it("stays true across re-renders", () => {
    const { result, rerender } = renderHook(() => useIsHydrated());
    rerender();
    expect(result.current).toBe(true);
  });
});
