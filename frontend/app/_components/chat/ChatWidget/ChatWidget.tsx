"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useFloatingDock } from "@/app/_components/floating/FloatingDockContext";
import { ChatIcon } from "@/app/_components/icons";
import { PetPicker, type PetPickerOption } from "@/app/_components/pets/PetPicker";
import { listPetsForBrowser, toPetPickerOption } from "@/lib/pets";
import { ChatComposer } from "../ChatComposer";
import { ChatTranscript } from "../ChatTranscript";
import { useChat } from "../useChat";
import styles from "./ChatWidget.module.css";

type PetsState =
  | { status: "idle" | "loading" | "error" }
  | { status: "ready"; pets: PetPickerOption[] };

export function ChatWidget() {
  const pathname = usePathname();
  const { setChatOpen } = useFloatingDock();
  const [open, setOpen] = useState(false);
  const [petsState, setPetsState] = useState<PetsState>({ status: "idle" });

  // Publish open state so the journal FAB can hide while the panel is expanded.
  useEffect(() => {
    setChatOpen(open);
  }, [open, setChatOpen]);

  if (pathname === "/chat") return null;

  async function loadPets() {
    setPetsState({ status: "loading" });
    try {
      const pets = await listPetsForBrowser();
      setPetsState({ status: "ready", pets: pets.map(toPetPickerOption) });
    } catch {
      setPetsState({ status: "error" });
    }
  }

  function handleToggle() {
    const next = !open;
    setOpen(next);
    if (next && petsState.status === "idle") void loadPets();
  }

  return (
    <div className={styles.root}>
      {open && (
        <section className={styles.panel} aria-label="Ask PawPilot">
          <header className={styles.panelHeader}>
            <span className={styles.panelTitle}>Ask PawPilot</span>
            <button
              type="button"
              className={styles.close}
              onClick={() => setOpen(false)}
              aria-label="Close chat"
            >
              ×
            </button>
          </header>
          <div className={styles.panelBody}>
            {petsState.status === "loading" && <p className={styles.hint}>Loading…</p>}
            {petsState.status === "error" && (
              <div className={styles.hint}>
                <p>Couldn&apos;t load your dogs.</p>
                <button type="button" className={styles.retry} onClick={() => void loadPets()}>
                  Try again
                </button>
              </div>
            )}
            {petsState.status === "ready" && petsState.pets.length === 0 && (
              <p className={styles.hint}>Add a dog to start asking about their health.</p>
            )}
            {petsState.status === "ready" && petsState.pets.length > 0 && (
              <ChatPanel pets={petsState.pets} />
            )}
          </div>
        </section>
      )}
      <button
        type="button"
        className={styles.launcher}
        onClick={handleToggle}
        aria-expanded={open}
        aria-label={open ? "Close PawPilot chat" : "Ask PawPilot"}
      >
        <ChatIcon size={24} />
      </button>
    </div>
  );
}

function ChatPanel({ pets }: { pets: PetPickerOption[] }) {
  const chat = useChat(pets);

  return (
    <>
      <div className={styles.panelControls}>
        <PetPicker
          pets={pets}
          activePetId={chat.activePetId}
          onSelect={chat.setActivePetId}
          align="start"
        />
        <button type="button" className={styles.newChat} onClick={chat.newConversation}>
          New
        </button>
      </div>
      <ChatTranscript
        messages={chat.messages}
        className={styles.transcript}
        emptyState={
          <p className={styles.empty}>
            Ask anything about {chat.activePet.name} — every answer cites its sources.
          </p>
        }
      />
      <div className={styles.composerWrap}>
        <ChatComposer
          onSend={chat.sendMessage}
          onStop={chat.stop}
          streaming={chat.pending}
          disabled={chat.pending}
        />
      </div>
    </>
  );
}
