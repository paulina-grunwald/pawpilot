import { getApiBaseUrl } from "./auth";

export type CitationKind = "corpus" | "web";

export type Citation = {
  ref: string;
  kind: CitationKind;
  title: string;
  url: string;
  source_id: string | null;
  source_tier: string | null;
  page_start: number | null;
};

export type AgentAskInput = {
  query: string;
  petId?: string;
  threadId?: string;
};

export type AgentStreamEvent =
  | { type: "token"; text: string }
  | { type: "final"; citations: Citation[]; emergency: boolean; tool_calls: string[] }
  | { type: "error"; detail: string };

export type ThreadMessageRole = "user" | "assistant";

export type AgentThreadSummary = {
  thread_id: string;
  pet_id: string | null;
  title: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentThreadMessage = {
  role: ThreadMessageRole;
  text: string;
};

export type AgentThreadDetail = {
  thread_id: string;
  pet_id: string | null;
  title: string | null;
  messages: AgentThreadMessage[];
};

export type AgentErrorCode =
  | "AGENT_UNAUTHENTICATED"
  | "AGENT_VALIDATION"
  | "AGENT_UNAVAILABLE"
  | "NETWORK_ERROR"
  | "UNKNOWN";

export class AgentError extends Error {
  readonly code: AgentErrorCode;
  readonly status?: number;

  constructor(code: AgentErrorCode, message: string, status?: number) {
    super(message);
    this.code = code;
    this.status = status;
    this.name = "AgentError";
  }
}

function agentErrorForStatus(status: number): AgentErrorCode {
  if (status === 401) return "AGENT_UNAUTHENTICATED";
  if (status === 422) return "AGENT_VALIDATION";
  if (status === 503) return "AGENT_UNAVAILABLE";
  return "UNKNOWN";
}

function parseSseEvent(raw: string): AgentStreamEvent | null {
  const dataLine = raw.split(/\r?\n/).find((line) => line.startsWith("data:"));
  if (!dataLine) return null;
  const payload = dataLine.slice(dataLine.indexOf(":") + 1).trim();
  if (!payload) return null;
  try {
    return JSON.parse(payload) as AgentStreamEvent;
  } catch {
    return null;
  }
}

async function getAgentJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}${path}`, {
      method: "GET",
      credentials: "include",
    });
  } catch (caught) {
    throw new AgentError(
      "NETWORK_ERROR",
      caught instanceof Error ? caught.message : String(caught),
    );
  }
  if (!response.ok) {
    throw new AgentError(
      agentErrorForStatus(response.status),
      `GET ${path} failed with ${response.status}`,
      response.status,
    );
  }
  return (await response.json()) as T;
}

/** List the current user's past conversations, newest first, optionally for one dog. */
export async function listThreads(petId?: string): Promise<AgentThreadSummary[]> {
  const query = petId ? `?pet_id=${encodeURIComponent(petId)}` : "";
  return getAgentJson<AgentThreadSummary[]>(`/agent/threads${query}`);
}

/** Fetch a past conversation's reconstructed transcript. */
export async function getThread(threadId: string): Promise<AgentThreadDetail> {
  return getAgentJson<AgentThreadDetail>(`/agent/threads/${encodeURIComponent(threadId)}`);
}

export async function* streamAgentAnswer(
  input: AgentAskInput,
  signal?: AbortSignal,
): AsyncGenerator<AgentStreamEvent> {
  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}/agent/ask/stream`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        query: input.query,
        pet_id: input.petId,
        thread_id: input.threadId,
      }),
      signal,
    });
  } catch (caught) {
    if (caught instanceof Error && caught.name === "AbortError") throw caught;
    throw new AgentError(
      "NETWORK_ERROR",
      caught instanceof Error ? caught.message : String(caught),
    );
  }

  if (!response.ok || !response.body) {
    throw new AgentError(
      agentErrorForStatus(response.status),
      `POST /agent/ask/stream failed with ${response.status}`,
      response.status,
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    buffer = buffer.replace(/\r\n?/g, "\n");
    let separatorIndex = buffer.indexOf("\n\n");
    while (separatorIndex !== -1) {
      const event = parseSseEvent(buffer.slice(0, separatorIndex));
      buffer = buffer.slice(separatorIndex + 2);
      if (event) yield event;
      separatorIndex = buffer.indexOf("\n\n");
    }
  }
}
