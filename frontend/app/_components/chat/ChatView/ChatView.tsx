"use client";

import { PetPicker, type PetPickerOption } from "@/app/_components/pets/PetPicker";
import { ChatComposer } from "../ChatComposer";
import { ChatTranscript } from "../ChatTranscript";
import { useChat } from "../useChat";
import styles from "./ChatView.module.css";

export function ChatView({ pets }: { pets: PetPickerOption[] }) {
  const chat = useChat(pets);

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
          <PetPicker pets={pets} activePetId={chat.activePetId} onSelect={chat.setActivePetId} />
          <button type="button" className={styles.newChat} onClick={chat.newConversation}>
            New conversation
          </button>
        </div>
      </header>

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
