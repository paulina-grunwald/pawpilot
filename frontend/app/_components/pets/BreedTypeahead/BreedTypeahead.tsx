"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { searchBreeds, type BreedRead } from "@/lib/breeds";
import styles from "./BreedTypeahead.module.css";

const DEBOUNCE_MS = 200;
const LIST_LIMIT = 20;

type BreedTypeaheadProps = {
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  inputId?: string;
  invalid?: boolean;
  describedBy?: string;
};

function highlightMatch(name: string, query: string): ReactNode {
  if (!query) return name;
  const haystack = name.toLowerCase();
  const needle = query.toLowerCase();
  const matchIndex = haystack.indexOf(needle);
  if (matchIndex < 0) return name;
  return (
    <>
      {name.slice(0, matchIndex)}
      <mark className={styles.match}>
        {name.slice(matchIndex, matchIndex + needle.length)}
      </mark>
      {name.slice(matchIndex + needle.length)}
    </>
  );
}

export function BreedTypeahead({
  value,
  onChange,
  onBlur,
  inputId,
  invalid,
  describedBy,
}: BreedTypeaheadProps) {
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const reactId = useId();
  const listboxId = `breed-listbox-${reactId}`;
  const optionId = (index: number) => `breed-option-${reactId}-${index}`;

  const [results, setResults] = useState<BreedRead[]>([]);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const fetched = await searchBreeds(value.trim(), LIST_LIMIT);
        if (!cancelled) {
          setResults(fetched);
          setHighlight(0);
        }
      } catch {
        if (!cancelled) setResults([]);
      }
    }, DEBOUNCE_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [value, open]);

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

  function commitSelection(breed: BreedRead) {
    onChange(breed.name);
    setOpen(false);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (!open) setOpen(true);
      setHighlight((prev) => Math.min(prev + 1, Math.max(results.length - 1, 0)));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlight((prev) => Math.max(prev - 1, 0));
    } else if (event.key === "Enter") {
      if (open && results[highlight]) {
        event.preventDefault();
        commitSelection(results[highlight]);
      }
    } else if (event.key === "Escape") {
      if (open) {
        event.preventDefault();
        setOpen(false);
      }
    }
  }

  const activeOptionId = open && results[highlight] ? optionId(highlight) : undefined;

  return (
    <div ref={wrapperRef} className={styles.wrapper}>
      <input
        id={inputId}
        type="text"
        autoComplete="off"
        className={styles.input}
        value={value}
        onChange={(event) => {
          onChange(event.target.value);
          if (!open) setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={onBlur}
        onKeyDown={onKeyDown}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-activedescendant={activeOptionId}
        aria-invalid={invalid ? "true" : undefined}
        aria-describedby={describedBy}
        placeholder="Start typing a breed…"
      />
      {open && (
        <div id={listboxId} role="listbox" className={styles.listbox}>
          {results.length === 0 && value.trim() && (
            <div className={styles.empty}>
              No matches. You can keep typing — we&rsquo;ll save whatever you write.
            </div>
          )}
          {results.length === 0 && !value.trim() && (
            <div className={styles.empty}>Loading breeds…</div>
          )}
          {results.length > 0 && value.trim().length === 0 && (
            <div className={styles.hint}>Popular breeds</div>
          )}
          {results.map((breed, index) => {
            const optionClasses = [
              styles.option,
              index === highlight ? styles.optionHighlighted : "",
            ]
              .filter(Boolean)
              .join(" ");
            return (
              <div
                key={breed.name}
                id={optionId(index)}
                role="option"
                aria-selected={breed.name === value}
                className={optionClasses}
                onMouseDown={(event) => {
                  event.preventDefault();
                  commitSelection(breed);
                }}
                onMouseEnter={() => setHighlight(index)}
              >
                <span>{highlightMatch(breed.name, value.trim())}</span>
                {breed.group && <span className={`${styles.optionGroup} mono`}>{breed.group}</span>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
