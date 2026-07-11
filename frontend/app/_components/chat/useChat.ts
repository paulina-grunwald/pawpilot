"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { PetPickerOption } from "@/app/_components/pets/PetPicker";
import { AgentError, streamAgentAnswer } from "@/lib/agent";
import type { ChatMessageModel } from "./ChatMessage";

type TranscriptMap = Record<string, ChatMessageModel[]>;

const THREAD_KEY_PREFIX = "pawpilot.chat.thread.";
const TRANSCRIPT_KEY_PREFIX = "pawpilot.chat.transcript.";
const UNAVAILABLE_MESSAGE = "PawPilot is unavailable right now. Please try again in a moment.";
const EXPIRED_MESSAGE = "Your session has expired. Please sign in again.";

function newId(): string {
  return crypto.randomUUID();
}

function loadTranscript(petId: string): ChatMessageModel[] {
  try {
    const raw = window.localStorage.getItem(`${TRANSCRIPT_KEY_PREFIX}${petId}`);
    return raw ? (JSON.parse(raw) as ChatMessageModel[]) : [];
  } catch {
    return [];
  }
}

function loadAllTranscripts(pets: PetPickerOption[]): TranscriptMap {
  const transcripts: TranscriptMap = {};
  for (const pet of pets) transcripts[pet.id] = loadTranscript(pet.id);
  return transcripts;
}

function saveTranscript(petId: string, messages: ChatMessageModel[]): void {
  try {
    window.localStorage.setItem(`${TRANSCRIPT_KEY_PREFIX}${petId}`, JSON.stringify(messages));
  } catch {
    return;
  }
}

function getThreadId(petId: string): string {
  const key = `${THREAD_KEY_PREFIX}${petId}`;
  const existing = window.localStorage.getItem(key);
  if (existing) return existing;
  const created = newId();
  window.localStorage.setItem(key, created);
  return created;
}

export type ChatController = {
  activePetId: string;
  activePet: PetPickerOption;
  setActivePetId: (petId: string) => void;
  messages: ChatMessageModel[];
  pending: boolean;
  sendMessage: (query: string) => Promise<void>;
  stop: () => void;
  newConversation: () => void;
};

export function useChat(pets: PetPickerOption[]): ChatController {
  const [activePetId, setActivePetId] = useState(pets[0].id);
  const [transcripts, setTranscripts] = useState<TranscriptMap>(() => loadAllTranscripts(pets));
  const [pending, setPending] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const messages = useMemo(() => transcripts[activePetId] ?? [], [transcripts, activePetId]);

  useEffect(() => {
    saveTranscript(activePetId, messages);
  }, [activePetId, messages]);

  const updateMessage = useCallback(
    (id: string, update: (message: ChatMessageModel) => ChatMessageModel) => {
      setTranscripts((prev) => {
        const current = prev[activePetId] ?? [];
        return {
          ...prev,
          [activePetId]: current.map((message) => (message.id === id ? update(message) : message)),
        };
      });
    },
    [activePetId],
  );

  const sendMessage = useCallback(
    async (query: string) => {
      if (pending) return;
      const threadId = getThreadId(activePetId);
      const assistantId = newId();
      setTranscripts((prev) => ({
        ...prev,
        [activePetId]: [
          ...(prev[activePetId] ?? []),
          {
            id: newId(),
            role: "user",
            text: query,
            citations: [],
            emergency: false,
            streaming: false,
            errored: false,
          },
          {
            id: assistantId,
            role: "assistant",
            text: "",
            citations: [],
            emergency: false,
            streaming: true,
            errored: false,
          },
        ],
      }));
      setPending(true);
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        for await (const event of streamAgentAnswer(
          { query, petId: activePetId, threadId },
          controller.signal,
        )) {
          if (event.type === "token") {
            updateMessage(assistantId, (message) => ({
              ...message,
              text: message.text + event.text,
            }));
          } else if (event.type === "final") {
            updateMessage(assistantId, (message) => ({
              ...message,
              citations: event.citations,
              emergency: event.emergency,
              streaming: false,
            }));
          } else {
            updateMessage(assistantId, (message) => ({
              ...message,
              streaming: false,
              errored: true,
              text: message.text || UNAVAILABLE_MESSAGE,
            }));
          }
        }
      } catch (caught) {
        const aborted = caught instanceof DOMException && caught.name === "AbortError";
        const expired = caught instanceof AgentError && caught.code === "AGENT_UNAUTHENTICATED";
        updateMessage(assistantId, (message) => ({
          ...message,
          streaming: false,
          errored: !aborted && message.text.length === 0,
          text: aborted
            ? message.text
            : message.text || (expired ? EXPIRED_MESSAGE : UNAVAILABLE_MESSAGE),
        }));
      } finally {
        setPending(false);
        abortRef.current = null;
      }
    },
    [activePetId, pending, updateMessage],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const newConversation = useCallback(() => {
    abortRef.current?.abort();
    window.localStorage.removeItem(`${THREAD_KEY_PREFIX}${activePetId}`);
    setTranscripts((prev) => ({ ...prev, [activePetId]: [] }));
  }, [activePetId]);

  const activePet = pets.find((pet) => pet.id === activePetId) ?? pets[0];

  return {
    activePetId,
    activePet,
    setActivePetId,
    messages,
    pending,
    sendMessage,
    stop,
    newConversation,
  };
}
