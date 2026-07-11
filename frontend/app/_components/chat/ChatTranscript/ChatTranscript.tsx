"use client";

import { type ReactNode, useEffect, useRef } from "react";
import { ChatMessage, type ChatMessageModel } from "../ChatMessage";

type ChatTranscriptProps = {
  messages: ChatMessageModel[];
  className: string;
  emptyState: ReactNode;
};

export function ChatTranscript({ messages, className, emptyState }: ChatTranscriptProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = scrollRef.current;
    node?.scrollTo?.({ top: node.scrollHeight, behavior: "smooth" });
  }, [messages]);

  return (
    <div ref={scrollRef} className={className}>
      {messages.length === 0
        ? emptyState
        : messages.map((message) => <ChatMessage key={message.id} message={message} />)}
    </div>
  );
}
