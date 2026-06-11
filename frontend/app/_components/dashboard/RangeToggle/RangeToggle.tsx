"use client";

import styles from "./RangeToggle.module.css";

export type RangeOption = {
  label: string;
  days: number;
};

type RangeToggleProps = {
  options: readonly RangeOption[];
  activeDays: number;
  onChange: (days: number) => void;
};

export function RangeToggle({ options, activeDays, onChange }: RangeToggleProps) {
  return (
    <div role="group" aria-label="Time range" className={styles.group}>
      {options.map((option) => {
        const isActive = option.days === activeDays;
        return (
          <button
            key={option.days}
            type="button"
            className={isActive ? styles.buttonActive : styles.button}
            aria-pressed={isActive}
            onClick={() => onChange(option.days)}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
