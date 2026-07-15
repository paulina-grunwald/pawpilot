const Y_PADDING_FRACTION = 0.18;
const DEFAULT_LABEL_SPACING = 46;

export type YBounds = { yMin: number; yMax: number };

export function clampIndex(index: number, count: number): number {
  if (count <= 0) return 0;
  return Math.max(0, Math.min(count - 1, index));
}

export function computeYBounds(
  values: readonly number[],
  extras: readonly number[] = [],
): YBounds {
  const all = [...values, ...extras];
  const min = Math.min(...all);
  const max = Math.max(...all);
  const span = max - min || 1;
  return {
    yMin: Math.max(0, min - span * Y_PADDING_FRACTION),
    yMax: max + span * Y_PADDING_FRACTION,
  };
}

export function labelStep(
  count: number,
  innerWidth: number,
  minSpacing: number = DEFAULT_LABEL_SPACING,
): number {
  const maxLabelCount = Math.max(2, Math.floor(innerWidth / minSpacing));
  return Math.max(1, Math.ceil(count / maxLabelCount));
}

export function isLabelVisibleFromEnd(index: number, count: number, step: number): boolean {
  const lastIndex = count - 1;
  return index === lastIndex || (lastIndex - index) % step === 0;
}

export type PointerToIndexParams = {
  clientX: number;
  boundsLeft: number;
  boundsWidth: number;
  chartWidth: number;
  paddingLeft: number;
  innerWidth: number;
  count: number;
  snap?: "round" | "floor";
};

export function pointerToIndex({
  clientX,
  boundsLeft,
  boundsWidth,
  chartWidth,
  paddingLeft,
  innerWidth,
  count,
  snap = "round",
}: PointerToIndexParams): number {
  const scale = boundsWidth === 0 ? 1 : chartWidth / boundsWidth;
  const localX = (clientX - boundsLeft) * scale;
  if (snap === "floor") {
    const slotWidth = innerWidth / count;
    return clampIndex(Math.floor((localX - paddingLeft) / slotWidth), count);
  }
  const ratio = (localX - paddingLeft) / innerWidth;
  return clampIndex(Math.round(ratio * (count - 1)), count);
}

export type TooltipPlacement = { x: number; y: number };

export type PlaceTooltipParams = {
  pointX: number;
  pointY: number;
  width: number;
  height: number;
  chartWidth: number;
  paddingLeft: number;
  paddingRight: number;
  paddingTop: number;
  offset?: number;
  overflow?: "flip" | "clamp";
};

export function placeTooltip({
  pointX,
  pointY,
  width,
  height,
  chartWidth,
  paddingLeft,
  paddingRight,
  paddingTop,
  offset = 10,
  overflow = "flip",
}: PlaceTooltipParams): TooltipPlacement {
  const x = Math.max(
    paddingLeft,
    Math.min(pointX - width / 2, chartWidth - paddingRight - width),
  );
  const preferredY = pointY - height - offset;
  if (preferredY >= paddingTop) return { x, y: preferredY };
  return { x, y: overflow === "flip" ? pointY + offset : paddingTop };
}
