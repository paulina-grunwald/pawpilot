import { describe, expect, it } from "vitest";
import {
  clampIndex,
  computeYBounds,
  isLabelVisibleFromEnd,
  labelStep,
  placeTooltip,
  pointerToIndex,
} from "./chartGeometry";

describe("clampIndex", () => {
  it("keeps in-range indices unchanged", () => {
    expect(clampIndex(3, 10)).toBe(3);
  });

  it("clamps below and above the range", () => {
    expect(clampIndex(-4, 10)).toBe(0);
    expect(clampIndex(99, 10)).toBe(9);
  });

  it("returns 0 for an empty collection", () => {
    expect(clampIndex(5, 0)).toBe(0);
  });
});

describe("computeYBounds", () => {
  it("pads the range above and below the data", () => {
    const { yMin, yMax } = computeYBounds([100, 200]);
    expect(yMin).toBeCloseTo(82);
    expect(yMax).toBeCloseTo(218);
  });

  it("never drops below zero", () => {
    expect(computeYBounds([0, 10]).yMin).toBe(0);
  });

  it("widens the range to include extra reference values", () => {
    const { yMax } = computeYBounds([100, 120], [400]);
    expect(yMax).toBeGreaterThan(400);
  });

  it("handles a flat series without dividing by zero", () => {
    const { yMin, yMax } = computeYBounds([50, 50]);
    expect(yMin).toBeLessThan(50);
    expect(yMax).toBeGreaterThan(50);
  });
});

describe("labelStep", () => {
  it("labels every point when they all fit", () => {
    expect(labelStep(7, 400)).toBe(1);
  });

  it("thins labels when there are many points in a narrow chart", () => {
    expect(labelStep(90, 148)).toBeGreaterThan(1);
  });
});

describe("isLabelVisibleFromEnd", () => {
  it("always labels the last index", () => {
    expect(isLabelVisibleFromEnd(89, 90, 30)).toBe(true);
  });

  it("labels indices stepping back from the end", () => {
    expect(isLabelVisibleFromEnd(59, 90, 30)).toBe(true);
    expect(isLabelVisibleFromEnd(58, 90, 30)).toBe(false);
  });
});

describe("pointerToIndex", () => {
  const base = {
    boundsLeft: 0,
    boundsWidth: 240,
    chartWidth: 240,
    paddingLeft: 38,
    innerWidth: 148,
    count: 4,
  };

  it("rounds to the nearest point by default", () => {
    expect(pointerToIndex({ ...base, clientX: 38 })).toBe(0);
    expect(pointerToIndex({ ...base, clientX: 38 + 148 })).toBe(3);
    expect(pointerToIndex({ ...base, clientX: 38 + 74 })).toBe(2);
  });

  it("clamps pointer positions outside the plot", () => {
    expect(pointerToIndex({ ...base, clientX: -100 })).toBe(0);
    expect(pointerToIndex({ ...base, clientX: 9999 })).toBe(3);
  });

  it("floors into the hovered slot for bar charts", () => {
    const slotWidth = base.innerWidth / base.count;
    expect(pointerToIndex({ ...base, clientX: 38 + slotWidth * 1.5, snap: "floor" })).toBe(1);
  });

  it("rescales when the rendered width differs from the chart width", () => {
    expect(pointerToIndex({ ...base, boundsWidth: 120, clientX: 56 })).toBe(2);
  });
});

describe("placeTooltip", () => {
  const base = {
    width: 50,
    height: 20,
    chartWidth: 240,
    paddingLeft: 38,
    paddingRight: 54,
    paddingTop: 18,
  };

  it("centres the box over the point when there is room", () => {
    const { x, y } = placeTooltip({ ...base, pointX: 120, pointY: 100 });
    expect(x).toBe(120 - 25);
    expect(y).toBe(100 - 20 - 10);
  });

  it("keeps the box within the horizontal bounds", () => {
    expect(placeTooltip({ ...base, pointX: 0, pointY: 100 }).x).toBe(38);
    expect(placeTooltip({ ...base, pointX: 240, pointY: 100 }).x).toBe(
      240 - 54 - 50,
    );
  });

  it("flips below the point when it would overflow the top", () => {
    const { y } = placeTooltip({ ...base, pointX: 120, pointY: 20, overflow: "flip" });
    expect(y).toBe(20 + 10);
  });

  it("clamps to the top edge instead of flipping when asked", () => {
    const { y } = placeTooltip({ ...base, pointX: 120, pointY: 20, overflow: "clamp" });
    expect(y).toBe(18);
  });
});
