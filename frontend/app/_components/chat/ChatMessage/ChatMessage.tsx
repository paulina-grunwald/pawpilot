import ReactMarkdown, { type Components } from "react-markdown";
import { PawMark } from "@/app/_components/PawMark";
import type { Citation } from "@/lib/agent";
import styles from "./ChatMessage.module.css";

const markdownComponents: Components = {
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noreferrer noopener">
      {children}
    </a>
  ),
};

export type ChatMessageModel = {
  id: string;
  role: "user" | "assistant";
  text: string;
  citations: Citation[];
  emergency: boolean;
  streaming: boolean;
  errored: boolean;
};

export function ChatMessage({ message }: { message: ChatMessageModel }) {
  if (message.role === "user") {
    return (
      <div className={`${styles.row} ${styles.rowUser}`}>
        <div className={`${styles.bubble} ${styles.bubbleUser}`}>{message.text}</div>
      </div>
    );
  }

  const awaitingFirstToken = message.streaming && message.text.length === 0;
  const bubbleClasses = [
    styles.bubble,
    styles.bubbleAssistant,
    message.emergency ? styles.bubbleEmergency : "",
    message.errored ? styles.bubbleErrored : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={`${styles.row} ${styles.rowAssistant}`}>
      <span className={styles.avatar} aria-hidden>
        <PawMark size={28} />
      </span>
      <div className={bubbleClasses}>
        {message.emergency && <span className={styles.emergencyTag}>Possibly urgent</span>}
        <div className={styles.text} aria-live={message.streaming ? "polite" : undefined}>
          {awaitingFirstToken ? (
            <span className={styles.thinking}>Thinking…</span>
          ) : (
            <>
              <div className={styles.markdown}>
                <ReactMarkdown components={markdownComponents}>{message.text}</ReactMarkdown>
              </div>
              {message.streaming && <span className={styles.caret} aria-hidden />}
            </>
          )}
        </div>
        {message.citations.length > 0 && <CitationList citations={message.citations} />}
      </div>
    </div>
  );
}

function CitationList({ citations }: { citations: Citation[] }) {
  return (
    <div className={styles.citations}>
      <span className={styles.citationsLabel}>Sources</span>
      <ul className={styles.citationList}>
        {citations.map((citation) => (
          <li key={citation.ref} className={styles.citation}>
            <span className={styles.citationRef}>[{citation.ref}]</span>
            {citation.url ? (
              <a
                className={styles.citationLink}
                href={citation.url}
                target="_blank"
                rel="noreferrer noopener"
              >
                {citation.title}
              </a>
            ) : (
              <span>{citation.title}</span>
            )}
            <span className={styles.citationKind}>{citation.kind}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
