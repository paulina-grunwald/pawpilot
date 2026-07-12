"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useFloatingDock } from "@/app/_components/floating/FloatingDockContext";
import { ChatIcon } from "@/app/_components/icons";
import type { PetPickerOption } from "@/app/_components/pets/PetPicker";
import { listPetsForBrowser, toPetPickerOption } from "@/lib/pets";
import { ChatComposer } from "../ChatComposer";
import { ChatHistory } from "../ChatHistory";
import { ChatTranscript } from "../ChatTranscript";
import { useActivePetId } from "../useActivePetId";
import { useChat } from "../useChat";
import styles from "./ChatWidget.module.css";

type PetsState =
  | { status: "idle" | "loading" | "error" }
  | { status: "ready"; pets: PetPickerOption[] };

export function ChatWidget({ userId }: { userId: string }) {
  const pathname = usePathname();
  const { setChatOpen } = useFloatingDock();
  const [open, setOpen] = useState(false);
  const [petsState, setPetsState] = useState<PetsState>({ status: "idle" });

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
              <ChatPanel pets={petsState.pets} userId={userId} />
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

function ChatPanel({ pets, userId }: { pets: PetPickerOption[]; userId: string }) {
  const activePetId = useActivePetId(pets, userId);
  const chat = useChat(pets, activePetId);
  const [historyOpen, setHistoryOpen] = useState(false);

  function toggleHistory() {
    setHistoryOpen((open) => {
      if (!open) void chat.refreshThreads();
      return !open;
    });
  }

  function handleSelectThread(threadId: string) {
    void chat.selectThread(threadId);
    setHistoryOpen(false);
  }

  function handleNewConversation() {
    chat.newConversation();
    setHistoryOpen(false);
  }

  return (
    <>
      <div className={styles.panelControls}>
        <span className={styles.activePet}>{chat.activePet.name}</span>
        <div className={styles.controlButtons}>
          <button
            type="button"
            className={styles.newChat}
            onClick={toggleHistory}
            aria-pressed={historyOpen}
          >
            {historyOpen ? "Close" : "History"}
          </button>
          <button type="button" className={styles.newChat} onClick={handleNewConversation}>
            New
          </button>
        </div>
      </div>
      {historyOpen ? (
        <ChatHistory
          threads={chat.threads}
          activeThreadId={chat.activeThreadId}
          loading={chat.threadsLoading}
          onSelect={handleSelectThread}
          onNewConversation={handleNewConversation}
        />
      ) : (
        <ChatTranscript
          messages={chat.messages}
          className={styles.transcript}
          emptyState={
            <p className={styles.empty}>
              Ask anything about {chat.activePet.name} — every answer cites its sources.
            </p>
          }
        />
      )}
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
