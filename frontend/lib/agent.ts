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
