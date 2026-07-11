"use client";

import Link from "next/link";
import {
  useEffect,
  useRef,
  useState,
  type ComponentType,
  type CSSProperties,
} from "react";
import {
  AlertIcon,
  BathroomIcon,
  CloseIcon,
  JournalIcon,
  MealIcon,
  MoodIcon,
  MoreIcon,
  type IconProps,
} from "@/app/_components/icons";
import { PetPicker, type PetPickerOption } from "@/app/_components/pets/PetPicker";
import type { EntryType } from "@/lib/journal.constants";
import { listPetsForBrowser, toPetPickerOption } from "@/lib/pets";
import { QuickAddModal } from "../../journal/QuickAddModal";
import { useFloatingDock } from "../FloatingDockContext";
import styles from "./JournalFab.module.css";

type QuickAction = {
  entryType: EntryType;
  label: string;
  icon: ComponentType<IconProps>;
  accentVar: string;
};

const QUICK_ACTIONS: readonly QuickAction[] = [
  { entryType: "meal", label: "Meal", icon: MealIcon, accentVar: "--warm" },
  { entryType: "bathroom", label: "Bathroom", icon: BathroomIcon, accentVar: "--ochre" },
  { entryType: "symptom", label: "Symptom", icon: AlertIcon, accentVar: "--terracotta" },
  { entryType: "mood", label: "Mood", icon: MoodIcon, accentVar: "--forest" },
];

const SAVED_MESSAGE_DURATION_MS = 2400;

type PetsState =
  | { status: "idle" | "loading" | "error" }
  | { status: "ready"; pets: PetPickerOption[] };

export function activePetStorageKey(userId: string): string {
  return `pawpilot:active-pet:${userId}`;
}

function resolveActivePetId(pets: PetPickerOption[], userId: string): string {
  const stored = window.localStorage.getItem(activePetStorageKey(userId));
  if (stored && pets.some((pet) => pet.id === stored)) return stored;
  return pets[0].id;
}

type JournalFabProps = {
  userId: string;
};

export function JournalFab({ userId }: JournalFabProps) {
  const { chatOpen } = useFloatingDock();
  const [menuOpen, setMenuOpen] = useState(false);
  const [petsState, setPetsState] = useState<PetsState>({ status: "idle" });
  const [activePetId, setActivePetId] = useState<string | null>(null);
  const [openType, setOpenType] = useState<EntryType | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const launcherRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!menuOpen) return;
    function onPointerDown(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
        launcherRef.current?.focus();
      }
    }
    window.addEventListener("mousedown", onPointerDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onPointerDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  useEffect(() => {
    if (!savedMessage) return;
    const timer = setTimeout(() => setSavedMessage(null), SAVED_MESSAGE_DURATION_MS);
    return () => clearTimeout(timer);
  }, [savedMessage]);

  // The chat panel opens upward over this corner, so yield the space to it.
  if (chatOpen) return null;

  async function loadPets() {
    setPetsState({ status: "loading" });
    try {
      const pets = (await listPetsForBrowser()).map(toPetPickerOption);
      setPetsState({ status: "ready", pets });
      if (pets.length > 0) {
        setActivePetId((current) => current ?? resolveActivePetId(pets, userId));
      }
    } catch {
      setPetsState({ status: "error" });
    }
  }

  function toggleMenu() {
    const next = !menuOpen;
    setMenuOpen(next);
    if (next) {
      setSavedMessage(null);
      if (petsState.status === "idle") void loadPets();
    }
  }

  function selectPet(petId: string) {
    setActivePetId(petId);
    window.localStorage.setItem(activePetStorageKey(userId), petId);
  }

  function openModalFor(entryType: EntryType | null) {
    setOpenType(entryType);
    setModalOpen(true);
    setMenuOpen(false);
  }

  const activePet =
    petsState.status === "ready"
      ? (petsState.pets.find((pet) => pet.id === activePetId) ?? petsState.pets[0])
      : undefined;

  return (
    <div ref={rootRef} className={styles.root}>
      {menuOpen && (
        <div
          className={styles.menu}
          role="group"
          aria-label={activePet ? `Log a journal entry for ${activePet.name}` : "Log a journal entry"}
        >
          {petsState.status === "loading" && <p className={styles.hint}>Loading…</p>}

          {petsState.status === "error" && (
            <div className={styles.hint}>
              <span>Couldn&apos;t load your dogs.</span>
              <button type="button" className={styles.retry} onClick={() => void loadPets()}>
                Try again
              </button>
            </div>
          )}

          {petsState.status === "ready" && petsState.pets.length === 0 && (
            <Link href="/pets/new" className={styles.hintLink} onClick={() => setMenuOpen(false)}>
              Add a dog to start logging →
            </Link>
          )}

          {petsState.status === "ready" && activePet && (
            <>
              {petsState.pets.length > 1 && (
                <div className={styles.petRow}>
                  <PetPicker
                    pets={petsState.pets}
                    activePetId={activePet.id}
                    onSelect={selectPet}
                    align="end"
                  />
                </div>
              )}
              {QUICK_ACTIONS.map((action, index) => {
                const Icon = action.icon;
                return (
                  <div
                    key={action.entryType}
                    className={styles.item}
                    style={{ animationDelay: `${index * 32}ms` }}
                  >
                    <span className={styles.itemLabel}>{action.label}</span>
                    <button
                      type="button"
                      className={styles.miniFab}
                      style={{ "--fab-accent": `var(${action.accentVar})` } as CSSProperties}
                      onClick={() => openModalFor(action.entryType)}
                      aria-label={`Log ${action.label.toLowerCase()}`}
                    >
                      <Icon size={20} color="var(--paper)" />
                    </button>
                  </div>
                );
              })}
              <div
                className={styles.item}
                style={{ animationDelay: `${QUICK_ACTIONS.length * 32}ms` }}
              >
                <span className={styles.itemLabel}>More…</span>
                <button
                  type="button"
                  className={`${styles.miniFab} ${styles.miniFabNeutral}`}
                  onClick={() => openModalFor(null)}
                  aria-label="More entry types"
                >
                  <MoreIcon size={20} />
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {savedMessage && (
        <span role="status" className={styles.savedToast}>
          {savedMessage}
        </span>
      )}

      <button
        ref={launcherRef}
        type="button"
        className={styles.launcher}
        onClick={toggleMenu}
        aria-expanded={menuOpen}
        aria-haspopup="menu"
        aria-label={menuOpen ? "Close journal menu" : "Log a journal entry"}
      >
        {menuOpen ? <CloseIcon size={24} /> : <JournalIcon size={24} />}
      </button>

      {activePet && (
        <QuickAddModal
          petId={activePet.id}
          petName={activePet.name}
          open={modalOpen}
          initialEntryType={openType}
          onClose={() => setModalOpen(false)}
          onSaved={() => {
            setModalOpen(false);
            setSavedMessage("Logged ✓");
          }}
        />
      )}
    </div>
  );
}
