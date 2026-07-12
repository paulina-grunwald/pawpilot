"use client";

import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import type { PetPickerOption } from "@/app/_components/pets/PetPicker";
import {
  AgentError,
  type AgentThreadMessage,
  type AgentThreadSummary,
  getThread,
  listThreads,
  streamAgentAnswer,
} from "@/lib/agent";
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

function peekThreadId(petId: string): string | null {
  try {
    return window.localStorage.getItem(`${THREAD_KEY_PREFIX}${petId}`);
  } catch {
    return null;
  }
}

function setThreadId(petId: string, threadId: string): void {
  try {
    window.localStorage.setItem(`${THREAD_KEY_PREFIX}${petId}`, threadId);
  } catch {
    return;
  }
}

function clearThreadId(petId: string): void {
  try {
    window.localStorage.removeItem(`${THREAD_KEY_PREFIX}${petId}`);
  } catch {
    return;
  }
}

function messagesFromThread(messages: AgentThreadMessage[]): ChatMessageModel[] {
  return messages.map((message) => ({
    id: newId(),
    role: message.role,
    text: message.text,
    citations: [],
    emergency: false,
    streaming: false,
    errored: false,
  }));
}

export type ChatController = {
  activePetId: string;
  activePet: PetPickerOption;
  messages: ChatMessageModel[];
  pending: boolean;
  threads: AgentThreadSummary[];
  threadsLoading: boolean;
  activeThreadId: string | null;
  refreshThreads: () => Promise<void>;
  selectThread: (threadId: string) => Promise<void>;
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

export function useChat(pets: PetPickerOption[], activePetId: string): ChatController {
  const hydrated = useHydrated();
  const [transcripts, setTranscripts] = useState<TranscriptMap>(() => loadAllTranscripts(pets));
  const [pendingPets, setPendingPets] = useState<PendingMap>({});
  const [threads, setThreads] = useState<AgentThreadSummary[]>([]);
  const [threadsLoading, setThreadsLoading] = useState(false);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
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

  // The active conversation and its history are per pet: re-read the current
  // thread and drop the previous dog's list when the focused pet changes.
  useEffect(() => {
    if (!hydrated) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setActiveThreadId(peekThreadId(activePetId));
    setThreads([]);
  }, [hydrated, activePetId]);

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
      setActiveThreadId(threadId);
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
        const aborted = caught instanceof Error && caught.name === "AbortError";
        const expired = caught instanceof AgentError && caught.code === "AGENT_UNAUTHENTICATED";
        updateMessage(petId, assistantId, (message) => ({
          ...message,
          streaming: false,
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

  const refreshThreads = useCallback(async () => {
    setThreadsLoading(true);
    try {
      setThreads(await listThreads(activePetId));
    } catch {
      setThreads([]);
    } finally {
      setThreadsLoading(false);
    }
  }, [activePetId]);

  const selectThread = useCallback(
    async (threadId: string) => {
      const petId = activePetId;
      abortControllers.current.get(petId)?.abort();
      try {
        const detail = await getThread(threadId);
        setTranscripts((prev) => ({ ...prev, [petId]: messagesFromThread(detail.messages) }));
        setThreadId(petId, threadId);
        setActiveThreadId(threadId);
      } catch {
        // Keep the current transcript in place if the conversation can't be loaded.
      }
    },
    [activePetId],
  );

  const stop = useCallback(() => {
    abortControllers.current.get(activePetId)?.abort();
  }, [activePetId]);

  const newConversation = useCallback(() => {
    abortControllers.current.get(activePetId)?.abort();
    clearThreadId(activePetId);
    setActiveThreadId(null);
    setTranscripts((prev) => ({ ...prev, [activePetId]: [] }));
  }, [activePetId]);

  const activePet = pets.find((pet) => pet.id === activePetId) ?? pets[0];

  return {
    activePetId,
    activePet,
    messages,
    pending,
    threads,
    threadsLoading,
    activeThreadId,
    refreshThreads,
    selectThread,
    sendMessage,
    stop,
    newConversation,
  };
}
