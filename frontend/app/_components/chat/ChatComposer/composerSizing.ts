export const COMPOSER_MAX_HEIGHT = 160;

export type ComposerSizing = {
  height: number;
  overflowY: "hidden" | "auto";
};

export function resolveComposerSizing(
  contentHeight: number,
  maxHeight: number = COMPOSER_MAX_HEIGHT,
): ComposerSizing {
  if (contentHeight >= maxHeight) {
    return { height: maxHeight, overflowY: "auto" };
  }
  return { height: Math.max(contentHeight, 0), overflowY: "hidden" };
}
