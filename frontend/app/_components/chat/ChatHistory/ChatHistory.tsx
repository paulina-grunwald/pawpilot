"use client";

import type { AgentThreadSummary } from "@/lib/agent";
import styles from "./ChatHistory.module.css";

type ChatHistoryProps = {
  threads: AgentThreadSummary[];
  activeThreadId: string | null;
  loading: boolean;
  onSelect: (threadId: string) => void;
  onNewConversation: () => void;
};

const dateFormatter = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" });

function formatUpdated(isoTimestamp: string): string {
  const parsed = new Date(isoTimestamp);
  return Number.isNaN(parsed.getTime()) ? "" : dateFormatter.format(parsed);
}

export function ChatHistory({
  threads,
  activeThreadId,
  loading,
  onSelect,
  onNewConversation,
}: ChatHistoryProps) {
  return (
    <div className={styles.root} aria-label="Past conversations">
      <button type="button" className={styles.newConversation} onClick={onNewConversation}>
        + New conversation
      </button>

      {loading && <p className={styles.hint}>Loading…</p>}

      {!loading && threads.length === 0 && (
        <p className={styles.hint}>No past conversations yet.</p>
      )}

      {!loading && threads.length > 0 && (
        <ul className={styles.list}>
          {threads.map((thread) => {
            const isActive = thread.thread_id === activeThreadId;
            return (
              <li key={thread.thread_id}>
                <button
                  type="button"
                  className={`${styles.item} ${isActive ? styles.itemActive : ""}`}
                  aria-current={isActive ? "true" : undefined}
                  onClick={() => onSelect(thread.thread_id)}
                >
                  <span className={styles.itemTitle}>
                    {thread.title ?? "Untitled conversation"}
                  </span>
                  <span className={styles.itemDate}>{formatUpdated(thread.updated_at)}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
