"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import styles from "./PetPicker.module.css";

export type PetPickerOption = {
  id: string;
  name: string;
  breed: string;
};

type PetPickerProps = {
  pets: PetPickerOption[];
  activePetId: string;
  onSelect: (petId: string) => void;
  align?: "start" | "end";
};

export function PetPicker({ pets, activePetId, onSelect, align = "end" }: PetPickerProps) {
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const menuId = useId();
  const [open, setOpen] = useState(false);

  const activePet = pets.find((pet) => pet.id === activePetId) ?? pets[0];

  useEffect(() => {
    if (!open) return;
    function onMouseDown(event: MouseEvent) {
      if (!wrapperRef.current) return;
      if (!wrapperRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    window.addEventListener("mousedown", onMouseDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onMouseDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function handleSelect(petId: string) {
    onSelect(petId);
    setOpen(false);
    triggerRef.current?.focus();
  }

  return (
    <div ref={wrapperRef} className={styles.wrapper}>
      <button
        ref={triggerRef}
        type="button"
        className={styles.trigger}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span>{activePet?.name ?? "Pick a dog"}</span>
        <span aria-hidden className={styles.caret}>▾</span>
      </button>
      {open && (
        <ul
          id={menuId}
          role="listbox"
          aria-label="Switch active pet"
          className={`${styles.menu} ${align === "start" ? styles.menuStart : styles.menuEnd}`}
        >
          {pets.map((pet) => {
            const isActive = pet.id === activePetId;
            return (
              <li key={pet.id} role="presentation">
                <button
                  type="button"
                  role="option"
                  aria-selected={isActive}
                  className={`${styles.option} ${isActive ? styles.optionActive : ""}`}
                  onClick={() => handleSelect(pet.id)}
                >
                  <span>{pet.name}</span>
                  <span className={styles.optionMeta}>{pet.breed}</span>
                </button>
              </li>
            );
          })}
          <li role="presentation" aria-hidden>
            <span className={styles.divider} />
          </li>
          <li role="presentation">
            <Link href="/pets/new" className={styles.addLink}>
              + Add another dog
            </Link>
          </li>
        </ul>
      )}
    </div>
  );
}
