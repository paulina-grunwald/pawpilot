import { useRef, type KeyboardEvent } from "react";

type RadioItemProps = {
  ref: (element: HTMLButtonElement | null) => void;
  tabIndex: number;
  onKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void;
};

export function useRadioGroupNav(
  itemCount: number,
  selectedIndex: number,
  onSelect: (index: number) => void,
): (index: number) => RadioItemProps {
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const tabStopIndex = selectedIndex >= 0 ? selectedIndex : 0;

  function focusAndSelect(index: number) {
    const wrapped = (index + itemCount) % itemCount;
    itemRefs.current[wrapped]?.focus();
    onSelect(wrapped);
  }

  return (index) => ({
    ref: (element) => {
      itemRefs.current[index] = element;
    },
    tabIndex: index === tabStopIndex ? 0 : -1,
    onKeyDown: (event) => {
      if (event.key === "ArrowRight" || event.key === "ArrowDown") {
        event.preventDefault();
        focusAndSelect(index + 1);
      } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
        event.preventDefault();
        focusAndSelect(index - 1);
      }
    },
  });
}
