"use client";

import { useState } from "react";
import type { PetPickerOption } from "@/app/_components/pets/PetPicker";
import { ChatComposer } from "../ChatComposer";
import { ChatHistory } from "../ChatHistory";
import { ChatTranscript } from "../ChatTranscript";
import { useActivePetId } from "../useActivePetId";
import { useChat } from "../useChat";
import styles from "./ChatView.module.css";

export function ChatView({ pets, userId }: { pets: PetPickerOption[]; userId: string }) {
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
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Ask PawPilot</h1>
          <p className={styles.subtitle}>
            Grounded answers about {chat.activePet.name}, with sources.
          </p>
        </div>
        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.newChat}
            onClick={toggleHistory}
            aria-pressed={historyOpen}
          >
            {historyOpen ? "Close history" : "History"}
          </button>
          <button type="button" className={styles.newChat} onClick={handleNewConversation}>
            New conversation
          </button>
        </div>
      </header>

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
            <div className={styles.empty}>
              <p className={styles.emptyTitle}>Ask anything about {chat.activePet.name}.</p>
              <p className={styles.emptyHint}>
                Diet, symptoms, meds, breed-specific care — every answer cites its sources.
              </p>
            </div>
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
        <p className={styles.disclaimer}>
          PawPilot is not a substitute for a veterinarian. In an emergency, contact your vet.
        </p>
      </div>
    </main>
  );
}
