"use client";

import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import type { PetPickerOption } from "@/app/_components/pets/PetPicker";
import { AgentError, streamAgentAnswer } from "@/lib/agent";
import type { ChatMessageModel } from "./ChatMessage";

type TranscriptMap = Record<string, ChatMessageModel[]>;
type PendingMap = Record<string, boolean>;

const THREAD_KEY_PREFIX = "pawpilot.chat.thread.";
const TRANSCRIPT_KEY_PREFIX = "pawpilot.chat.transcript.";
const UNAVAILABLE_MESSAGE = "PawPilot is unavailable right now. Please try again in a moment.";
const EXPIRED_MESSAGE = "Your session has expired. Please sign in again.";

function newId(): string {
  return crypto.randomUUID();
}

function settleStreamingMessage(message: ChatMessageModel): ChatMessageModel {
  if (!message.streaming) return message;
  return { ...message, streaming: false, errored: message.errored || message.text.length === 0 };
}

function loadTranscript(petId: string): ChatMessageModel[] {
  try {
    const raw = window.localStorage.getItem(`${TRANSCRIPT_KEY_PREFIX}${petId}`);
    if (!raw) return [];
    return (JSON.parse(raw) as ChatMessageModel[]).map(settleStreamingMessage);
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
  try {
    const existing = window.localStorage.getItem(key);
    if (existing) return existing;
    const created = newId();
    window.localStorage.setItem(key, created);
    return created;
  } catch {
    return newId();
  }
}

function clearThreadId(petId: string): void {
  try {
    window.localStorage.removeItem(`${THREAD_KEY_PREFIX}${petId}`);
  } catch {
    return;
  }
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

const subscribeToNothing = () => () => {};

function useHydrated(): boolean {
  return useSyncExternalStore(
    subscribeToNothing,
    () => true,
    () => false,
  );
}

export function useChat(pets: PetPickerOption[]): ChatController {
  const hydrated = useHydrated();
  const [activePetId, setActivePetId] = useState(pets[0].id);
  const [transcripts, setTranscripts] = useState<TranscriptMap>(() => loadAllTranscripts(pets));
  const [pendingPets, setPendingPets] = useState<PendingMap>({});
  const abortControllers = useRef<Map<string, AbortController>>(new Map());

  const pending = pendingPets[activePetId] ?? false;
  const messages = useMemo(
    () => (hydrated ? (transcripts[activePetId] ?? []) : []),
    [hydrated, transcripts, activePetId],
  );

  useEffect(() => {
    if (!hydrated || pendingPets[activePetId]) return;
    saveTranscript(activePetId, messages);
  }, [hydrated, pendingPets, activePetId, messages]);

  useEffect(() => {
    const controllers = abortControllers.current;
    return () => {
      for (const controller of controllers.values()) controller.abort();
    };
  }, []);

  const updateMessage = useCallback(
    (petId: string, id: string, update: (message: ChatMessageModel) => ChatMessageModel) => {
      setTranscripts((prev) => {
        const current = prev[petId] ?? [];
        return {
          ...prev,
          [petId]: current.map((message) => (message.id === id ? update(message) : message)),
        };
      });
    },
    [],
  );

  const sendMessage = useCallback(
    async (query: string) => {
      const petId = activePetId;
      if (pendingPets[petId]) return;
      const threadId = getThreadId(petId);
      const assistantId = newId();
      setTranscripts((prev) => ({
        ...prev,
        [petId]: [
          ...(prev[petId] ?? []),
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
      setPendingPets((prev) => ({ ...prev, [petId]: true }));
      const controller = new AbortController();
      abortControllers.current.set(petId, controller);

      let settled = false;
      try {
        for await (const event of streamAgentAnswer(
          { query, petId, threadId },
          controller.signal,
        )) {
          if (event.type === "token") {
            updateMessage(petId, assistantId, (message) => ({
              ...message,
              text: message.text + event.text,
            }));
          } else if (event.type === "final") {
            settled = true;
            updateMessage(petId, assistantId, (message) => ({
              ...message,
              citations: event.citations,
              emergency: event.emergency,
              streaming: false,
            }));
          } else {
            settled = true;
            updateMessage(petId, assistantId, (message) => ({
              ...message,
              streaming: false,
              errored: true,
              text: message.text || UNAVAILABLE_MESSAGE,
            }));
          }
        }
        if (!settled) {
          updateMessage(petId, assistantId, (message) => ({
            ...message,
            streaming: false,
            errored: message.text.length === 0,
            text: message.text || UNAVAILABLE_MESSAGE,
          }));
        }
      } catch (caught) {
        const aborted = caught instanceof DOMException && caught.name === "AbortError";
        const expired = caught instanceof AgentError && caught.code === "AGENT_UNAUTHENTICATED";
        updateMessage(petId, assistantId, (message) => ({
          ...message,
          streaming: false,
          // Any non-abort failure is an error, even when partial text arrived —
          // a truncated answer must not be shown as if it completed normally.
          errored: !aborted,
          text: aborted
            ? message.text
            : message.text || (expired ? EXPIRED_MESSAGE : UNAVAILABLE_MESSAGE),
        }));
      } finally {
        setPendingPets((prev) => ({ ...prev, [petId]: false }));
        if (abortControllers.current.get(petId) === controller) {
          abortControllers.current.delete(petId);
        }
      }
    },
    [activePetId, pendingPets, updateMessage],
  );

  const stop = useCallback(() => {
    abortControllers.current.get(activePetId)?.abort();
  }, [activePetId]);

  const newConversation = useCallback(() => {
    abortControllers.current.get(activePetId)?.abort();
    clearThreadId(activePetId);
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
