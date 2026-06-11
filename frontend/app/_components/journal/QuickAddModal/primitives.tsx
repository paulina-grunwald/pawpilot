"use client";

import { useId, useState, type ReactNode } from "react";
import { MAX_TAG_LENGTH, MAX_TAGS } from "@/lib/journal.constants";
import styles from "./QuickAddModal.module.css";

type FieldLabelProps = {
  children: ReactNode;
  htmlFor?: string;
  optional?: boolean;
};

export function FieldLabel({ children, htmlFor, optional }: FieldLabelProps) {
  return (
    <label className={styles.fieldLabel} htmlFor={htmlFor}>
      {children}
      {optional && <span className={styles.optionalHint}> · optional</span>}
    </label>
  );
}

type PillOption<Value extends string> = {
  value: Value;
  label: string;
};

type PillRowProps<Value extends string> = {
  legend: string;
  options: readonly PillOption<Value>[];
  value: Value | null;
  onChange: (value: Value) => void;
};

export function PillRow<Value extends string>({
  legend,
  options,
  value,
  onChange,
}: PillRowProps<Value>) {
  return (
    <fieldset className={styles.pillFieldset}>
      <legend className={styles.fieldLabel}>{legend}</legend>
      <div className={styles.pillRow} role="radiogroup" aria-label={legend}>
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={option.value === value}
            className={`${styles.pill} ${option.value === value ? styles.pillActive : ""}`}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

type TagPickerProps = {
  legend: string;
  suggestions: readonly string[];
  value: string[];
  onChange: (tags: string[]) => void;
};

export function TagPicker({ legend, suggestions, value, onChange }: TagPickerProps) {
  const [customTag, setCustomTag] = useState("");
  const inputId = useId();
  const allTags = [...suggestions, ...value.filter((tag) => !suggestions.includes(tag))];

  function toggle(tag: string) {
    if (value.includes(tag)) {
      onChange(value.filter((existing) => existing !== tag));
    } else if (value.length < MAX_TAGS) {
      onChange([...value, tag]);
    }
  }

  function addCustom() {
    const trimmed = customTag.trim().slice(0, MAX_TAG_LENGTH);
    if (trimmed.length === 0) return;
    if (!value.includes(trimmed) && value.length < MAX_TAGS) {
      onChange([...value, trimmed]);
    }
    setCustomTag("");
  }

  return (
    <fieldset className={styles.pillFieldset}>
      <legend className={styles.fieldLabel}>{legend}</legend>
      <div className={styles.pillRow}>
        {allTags.map((tag) => {
          const active = value.includes(tag);
          return (
            <button
              key={tag}
              type="button"
              aria-pressed={active}
              className={`${styles.pill} ${active ? styles.pillActive : ""}`}
              onClick={() => toggle(tag)}
            >
              {tag}
            </button>
          );
        })}
      </div>
      <div className={styles.customTagRow}>
        <input
          id={inputId}
          type="text"
          className={styles.textInput}
          placeholder="Add a custom tag"
          maxLength={MAX_TAG_LENGTH}
          value={customTag}
          onChange={(event) => setCustomTag(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              addCustom();
            }
          }}
        />
        <button type="button" className={styles.secondaryButton} onClick={addCustom}>
          Add
        </button>
      </div>
    </fieldset>
  );
}

type NotesFieldProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
};

export function NotesField({ value, onChange, placeholder }: NotesFieldProps) {
  const id = useId();
  return (
    <div className={styles.field}>
      <FieldLabel htmlFor={id} optional>
        Note
      </FieldLabel>
      <textarea
        id={id}
        className={styles.textArea}
        rows={2}
        maxLength={1000}
        placeholder={placeholder ?? "Anything else worth remembering…"}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

type ScoreScaleProps = {
  legend: string;
  labels: Record<number, string>;
  value: number;
  onChange: (score: number) => void;
};

export function ScoreScale({ legend, labels, value, onChange }: ScoreScaleProps) {
  return (
    <fieldset className={styles.pillFieldset}>
      <legend className={styles.fieldLabel}>{legend}</legend>
      <div className={styles.scoreRow} role="radiogroup" aria-label={legend}>
        {[1, 2, 3, 4, 5].map((score) => (
          <button
            key={score}
            type="button"
            role="radio"
            aria-checked={score === value}
            className={`${styles.scoreButton} ${score === value ? styles.scoreButtonActive : ""}`}
            onClick={() => onChange(score)}
          >
            <span className={styles.scoreNumber}>{score}</span>
            <span className={styles.scoreLabel}>{labels[score]}</span>
          </button>
        ))}
      </div>
    </fieldset>
  );
}

type TextFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  optional?: boolean;
  maxLength?: number;
};

export function TextField({
  label,
  value,
  onChange,
  placeholder,
  optional,
  maxLength,
}: TextFieldProps) {
  const id = useId();
  return (
    <div className={styles.field}>
      <FieldLabel htmlFor={id} optional={optional}>
        {label}
      </FieldLabel>
      <input
        id={id}
        type="text"
        className={styles.textInput}
        placeholder={placeholder}
        maxLength={maxLength}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}
