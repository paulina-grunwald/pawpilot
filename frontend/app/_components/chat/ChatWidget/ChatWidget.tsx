"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ChatIcon } from "@/app/_components/icons";
import { PetPicker, type PetPickerOption } from "@/app/_components/pets/PetPicker";
import { listPetsForBrowser } from "@/lib/pets";
import { ChatComposer } from "../ChatComposer";
import { ChatMessage } from "../ChatMessage";
import { useChat } from "../useChat";
import styles from "./ChatWidget.module.css";

type PetsState =
  | { status: "idle" | "loading" | "error" }
  | { status: "ready"; pets: PetPickerOption[] };

export function ChatWidget() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [petsState, setPetsState] = useState<PetsState>({ status: "idle" });

  if (pathname === "/chat") return null;

  async function loadPets() {
    setPetsState({ status: "loading" });
    try {
      const pets = await listPetsForBrowser();
      setPetsState({
        status: "ready",
        pets: pets.map((pet) => ({
          id: pet.id,
          name: pet.name,
          breed: pet.breed_other ?? "Dog",
        })),
      });
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
              <p className={styles.hint}>Couldn&apos;t load your dogs. Please try again.</p>
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
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = scrollRef.current;
    node?.scrollTo?.({ top: node.scrollHeight, behavior: "smooth" });
  }, [chat.messages]);

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
      <div ref={scrollRef} className={styles.transcript}>
        {chat.messages.length === 0 ? (
          <p className={styles.empty}>
            Ask anything about {chat.activePet.name} — every answer cites its sources.
          </p>
        ) : (
          chat.messages.map((message) => <ChatMessage key={message.id} message={message} />)
        )}
      </div>
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
