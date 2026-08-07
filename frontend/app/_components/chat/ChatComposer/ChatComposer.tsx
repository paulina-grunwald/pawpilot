"use client";

import { type KeyboardEvent, useLayoutEffect, useRef, useState } from "react";
import styles from "./ChatComposer.module.css";
import { COMPOSER_MAX_HEIGHT, resolveComposerSizing } from "./composerSizing";

type ChatComposerProps = {
  onSend: (query: string) => void;
  onStop: () => void;
  streaming: boolean;
  disabled: boolean;
};

export function ChatComposer({ onSend, onStop, streaming, disabled }: ChatComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useLayoutEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    const { height, overflowY } = resolveComposerSizing(
      textarea.scrollHeight,
      COMPOSER_MAX_HEIGHT,
    );
    textarea.style.height = `${height}px`;
    textarea.style.overflowY = overflowY;
  }, [value]);

  function submit() {
    const query = value.trim();
    if (!query || disabled) return;
    onSend(query);
    setValue("");
    textareaRef.current?.focus();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form
      className={styles.composer}
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <textarea
        ref={textareaRef}
        className={styles.input}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about your dog's health…"
        rows={1}
        aria-label="Ask PawPilot a question"
      />
      {streaming ? (
        <button type="button" className={styles.stop} onClick={onStop}>
          Stop
        </button>
      ) : (
        <button
          type="submit"
          className={styles.send}
          disabled={disabled || value.trim().length === 0}
        >
          Send
        </button>
      )}
    </form>
  );
}
