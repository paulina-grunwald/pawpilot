import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { getApiBaseUrl } from "./auth";
import {
  AgentError,
  getThread,
  listThreads,
  streamAgentAnswer,
  type AgentStreamEvent,
} from "./agent";

const API = getApiBaseUrl();

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

async function collect(stream: AsyncGenerator<AgentStreamEvent>): Promise<AgentStreamEvent[]> {
  const events: AgentStreamEvent[] = [];
  for await (const event of stream) events.push(event);
  return events;
}

describe("AgentError", () => {
  it("captures code and status", () => {
    const error = new AgentError("AGENT_UNAVAILABLE", "down", 503);
    expect(error.code).toBe("AGENT_UNAVAILABLE");
    expect(error.status).toBe(503);
    expect(error).toBeInstanceOf(Error);
  });
});

describe("streamAgentAnswer", () => {
  it("parses token then final events from the SSE stream", async () => {
    const body =
      'data: {"type":"token","text":"Aussies "}\n\n' +
      'data: {"type":"token","text":"are active [S1]."}\n\n' +
      'data: {"type":"final","citations":[{"ref":"S1","kind":"corpus","title":"WSAVA","url":"https://ex/a","source_id":"s","source_tier":"guideline","page_start":12}],"emergency":false,"tool_calls":["retrieve_vet_corpus"]}\n\n';
    server.use(
      http.post(
        `${API}/agent/ask/stream`,
        () => new HttpResponse(body, { headers: { "content-type": "text/event-stream" } }),
      ),
    );

    const events = await collect(streamAgentAnswer({ query: "exercise?" }));
    const text = events.flatMap((event) => (event.type === "token" ? [event.text] : [])).join("");
    const final = events.find((event) => event.type === "final");
    expect(text).toBe("Aussies are active [S1].");
    expect(final).toMatchObject({ emergency: false, tool_calls: ["retrieve_vet_corpus"] });
    expect(final?.type === "final" && final.citations[0].ref).toBe("S1");
  });

  it("splits events that arrive across chunk boundaries", async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        const encoder = new TextEncoder();
        controller.enqueue(encoder.encode('data: {"type":"to'));
        controller.enqueue(encoder.encode('ken","text":"Hi"}\n\ndata: {"type":"fi'));
        controller.enqueue(
          encoder.encode('nal","citations":[],"emergency":true,"tool_calls":[]}\n\n'),
        );
        controller.close();
      },
    });
    server.use(
      http.post(
        `${API}/agent/ask/stream`,
        () => new HttpResponse(stream, { headers: { "content-type": "text/event-stream" } }),
      ),
    );

    const events = await collect(streamAgentAnswer({ query: "hi" }));
    expect(events).toEqual([
      { type: "token", text: "Hi" },
      { type: "final", citations: [], emergency: true, tool_calls: [] },
    ]);
  });

  it("throws AGENT_UNAVAILABLE on a 503", async () => {
    server.use(
      http.post(`${API}/agent/ask/stream`, () => new HttpResponse(null, { status: 503 })),
    );
    await expect(collect(streamAgentAnswer({ query: "hi" }))).rejects.toMatchObject({
      code: "AGENT_UNAVAILABLE",
    });
  });

  it("throws AGENT_VALIDATION on a 422", async () => {
    server.use(
      http.post(`${API}/agent/ask/stream`, () => new HttpResponse(null, { status: 422 })),
    );
    await expect(collect(streamAgentAnswer({ query: "" }))).rejects.toMatchObject({
      code: "AGENT_VALIDATION",
    });
  });

  it("parses events delimited by CRLF blank lines", async () => {
    const body =
      'data: {"type":"token","text":"Hi"}\r\n\r\n' +
      'data: {"type":"final","citations":[],"emergency":false,"tool_calls":[]}\r\n\r\n';
    server.use(
      http.post(
        `${API}/agent/ask/stream`,
        () => new HttpResponse(body, { headers: { "content-type": "text/event-stream" } }),
      ),
    );

    const events = await collect(streamAgentAnswer({ query: "hi" }));
    expect(events).toEqual([
      { type: "token", text: "Hi" },
      { type: "final", citations: [], emergency: false, tool_calls: [] },
    ]);
  });

  it("skips non-JSON data lines instead of aborting the whole stream", async () => {
    const body =
      "data: [DONE]\n\n" +
      'data: {"type":"token","text":"ok"}\n\n' +
      'data: {"type":"final","citations":[],"emergency":false,"tool_calls":[]}\n\n';
    server.use(
      http.post(
        `${API}/agent/ask/stream`,
        () => new HttpResponse(body, { headers: { "content-type": "text/event-stream" } }),
      ),
    );

    const events = await collect(streamAgentAnswer({ query: "hi" }));
    expect(events).toEqual([
      { type: "token", text: "ok" },
      { type: "final", citations: [], emergency: false, tool_calls: [] },
    ]);
  });

  it("re-throws an aborted request as a DOMException, not a NETWORK_ERROR", async () => {
    server.use(
      http.post(
        `${API}/agent/ask/stream`,
        () => new HttpResponse("data: {}\n\n", { headers: { "content-type": "text/event-stream" } }),
      ),
    );
    const controller = new AbortController();
    controller.abort();

    let caught: unknown;
    try {
      await collect(streamAgentAnswer({ query: "hi" }, controller.signal));
    } catch (error) {
      caught = error;
    }
    expect((caught as Error).name).toBe("AbortError");
    expect(caught).not.toBeInstanceOf(AgentError);
  });
});

describe("listThreads", () => {
  it("returns the user's conversations, filtered by pet", async () => {
    let requestedUrl = "";
    server.use(
      http.get(`${API}/agent/threads`, ({ request }) => {
        requestedUrl = request.url;
        return HttpResponse.json([
          {
            thread_id: "t1",
            pet_id: "pet-1",
            title: "Diet",
            created_at: "2026-07-10T00:00:00Z",
            updated_at: "2026-07-11T00:00:00Z",
          },
        ]);
      }),
    );

    const threads = await listThreads("pet-1");
    expect(threads).toHaveLength(1);
    expect(threads[0].title).toBe("Diet");
    expect(requestedUrl).toContain("pet_id=pet-1");
  });

  it("omits the pet filter when no pet is given", async () => {
    let requestedUrl = "";
    server.use(
      http.get(`${API}/agent/threads`, ({ request }) => {
        requestedUrl = request.url;
        return HttpResponse.json([]);
      }),
    );

    await listThreads();
    expect(requestedUrl).not.toContain("pet_id");
  });

  it("throws AGENT_UNAUTHENTICATED on a 401", async () => {
    server.use(http.get(`${API}/agent/threads`, () => new HttpResponse(null, { status: 401 })));
    await expect(listThreads()).rejects.toMatchObject({ code: "AGENT_UNAUTHENTICATED" });
  });
});

describe("getThread", () => {
  it("fetches a conversation's reconstructed transcript", async () => {
    server.use(
      http.get(`${API}/agent/threads/conv-1`, () =>
        HttpResponse.json({
          thread_id: "conv-1",
          pet_id: "pet-1",
          title: "Diet",
          messages: [
            { role: "user", text: "Diet?" },
            { role: "assistant", text: "Feed twice daily." },
          ],
        }),
      ),
    );

    const detail = await getThread("conv-1");
    expect(detail.messages.map((message) => message.role)).toEqual(["user", "assistant"]);
    expect(detail.messages[1].text).toBe("Feed twice daily.");
  });

  it("throws an AgentError on a 404", async () => {
    server.use(
      http.get(`${API}/agent/threads/nope`, () => new HttpResponse(null, { status: 404 })),
    );
    await expect(getThread("nope")).rejects.toBeInstanceOf(AgentError);
  });
});
