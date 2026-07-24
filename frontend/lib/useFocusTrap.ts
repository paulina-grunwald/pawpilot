import { useEffect, type RefObject } from "react";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

/**
 * Trap keyboard focus within `containerRef` while `active`.
 *
 * Tab / Shift+Tab cycle between the first and last focusable descendants
 * instead of escaping into the inert background, per the WAI-ARIA modal dialog
 * pattern. Focus is restored to the previously-focused element on teardown so
 * closing the dialog returns the user to where they were.
 *
 * The container itself should carry `tabIndex={-1}` so it can receive focus as
 * a fallback when it holds no focusable children.
 */
export function useFocusTrap(containerRef: RefObject<HTMLElement | null>, active = true): void {
  useEffect(() => {
    if (!active) return;
    const container = containerRef.current;
    if (!container) return;

    const previouslyFocused =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;

    function focusableElements(): HTMLElement[] {
      return Array.from(container!.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Tab") return;
      const elements = focusableElements();
      if (elements.length === 0) {
        event.preventDefault();
        container!.focus();
        return;
      }
      const first = elements[0];
      const last = elements[elements.length - 1];
      const currentlyFocused = document.activeElement;
      if (event.shiftKey) {
        if (currentlyFocused === first || !container!.contains(currentlyFocused)) {
          event.preventDefault();
          last.focus();
        }
      } else if (currentlyFocused === last || !container!.contains(currentlyFocused)) {
        event.preventDefault();
        first.focus();
      }
    }

    container.addEventListener("keydown", handleKeyDown);
    return () => {
      container.removeEventListener("keydown", handleKeyDown);
      previouslyFocused?.focus();
    };
  }, [containerRef, active]);
}
