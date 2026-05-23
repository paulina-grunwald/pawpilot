"use client";

import { useEffect, useRef, useState } from "react";
import { DayPicker } from "react-day-picker";
import "react-day-picker/style.css";
import styles from "./BirthdayField.module.css";

const MAX_AGE_YEARS = 22;

type BirthdayFieldProps = {
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  inputId?: string;
  invalid?: boolean;
  describedBy?: string;
};

function toIsoDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseIsoDate(value: string): Date | undefined {
  if (!value) return undefined;
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? undefined : parsed;
}

function formatDisplay(date: Date | undefined): string {
  if (!date) return "";
  return date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function BirthdayField({
  value,
  onChange,
  onBlur,
  inputId,
  invalid,
  describedBy,
}: BirthdayFieldProps) {
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const [open, setOpen] = useState(false);

  const selected = parseIsoDate(value);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const earliest = new Date(today);
  earliest.setFullYear(today.getFullYear() - MAX_AGE_YEARS);

  useEffect(() => {
    function onClickOutside(event: MouseEvent) {
      if (!wrapperRef.current) return;
      if (!wrapperRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    window.addEventListener("mousedown", onClickOutside);
    return () => window.removeEventListener("mousedown", onClickOutside);
  }, []);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  function handleSelect(date: Date | undefined) {
    if (!date) return;
    onChange(toIsoDate(date));
    setOpen(false);
    triggerRef.current?.focus();
  }

  const displayText = formatDisplay(selected);

  return (
    <div ref={wrapperRef} className={styles.wrapper}>
      <button
        id={inputId}
        ref={triggerRef}
        type="button"
        className={styles.trigger}
        aria-haspopup="dialog"
        aria-expanded={open}
        data-invalid={invalid ? "true" : undefined}
        aria-describedby={describedBy}
        onClick={() => setOpen((prev) => !prev)}
        onBlur={onBlur}
      >
        {displayText ? (
          <span>{displayText}</span>
        ) : (
          <span className={styles.placeholder}>Pick a date</span>
        )}
        <svg
          className={styles.icon}
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <rect x="3" y="5" width="18" height="16" rx="2" />
          <path d="M16 3v4M8 3v4M3 11h18" />
        </svg>
      </button>
      {open && (
        <div role="dialog" aria-label="Choose birthday" className={styles.popover}>
          <DayPicker
            className={styles.calendar}
            mode="single"
            selected={selected}
            onSelect={handleSelect}
            defaultMonth={selected ?? today}
            startMonth={earliest}
            endMonth={today}
            disabled={{ before: earliest, after: today }}
            captionLayout="dropdown"
            autoFocus
          />
        </div>
      )}
    </div>
  );
}
