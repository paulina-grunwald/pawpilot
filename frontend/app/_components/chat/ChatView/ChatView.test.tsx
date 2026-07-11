import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AgentAskInput, AgentStreamEvent } from "@/lib/agent";
import { ChatView } from "./ChatView";

const { streamMock } = vi.hoisted(() => ({ streamMock: vi.fn() }));

vi.mock("@/lib/agent", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/agent")>();
  return { ...actual, streamAgentAnswer: streamMock };
});

async function* scripted(events: AgentStreamEvent[]): AsyncGenerator<AgentStreamEvent> {
  for (const event of events) yield event;
}

const pets = [{ id: "pet-1", name: "Luna", breed: "Aussie" }];

afterEach(() => {
  streamMock.mockReset();
  window.localStorage.clear();
});

describe("ChatView", () => {
  it("shows the empty state before any message", () => {
    render(<ChatView pets={pets} />);
    expect(screen.getByText("Ask anything about Luna.")).toBeInTheDocument();
  });

  it("streams an answer with citations for a submitted question", async () => {
    streamMock.mockReturnValue(
      scripted([
        { type: "token", text: "Aussies " },
        { type: "token", text: "need lots of exercise [S1]." },
        {
          type: "final",
          citations: [
            {
              ref: "S1",
              kind: "corpus",
              title: "WSAVA",
              url: "https://ex/a",
              source_id: null,
              source_tier: null,
              page_start: null,
            },
          ],
          emergency: false,
          tool_calls: [],
        },
      ]),
    );
    const user = userEvent.setup();
    render(<ChatView pets={pets} />);

    await user.type(screen.getByRole("textbox", { name: /ask pawpilot/i }), "How much exercise?");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() =>
      expect(screen.getByText("Aussies need lots of exercise [S1].")).toBeInTheDocument(),
    );
    expect(screen.getByText("How much exercise?")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /wsava/i })).toHaveAttribute("href", "https://ex/a");
    expect(streamMock).toHaveBeenCalledWith(
      expect.objectContaining({ query: "How much exercise?", petId: "pet-1" }),
      expect.anything(),
    );
  });

  it("clears the composer when the stream ends without a final event", async () => {
    streamMock.mockReturnValue(scripted([{ type: "token", text: "Partial answer" }]));
    const user = userEvent.setup();
    render(<ChatView pets={pets} />);

    await user.type(screen.getByRole("textbox", { name: /ask pawpilot/i }), "hi");
    await user.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => expect(screen.getByText("Partial answer")).toBeInTheDocument());
    // Not stuck streaming: the composer returns to Send rather than a hung Stop.
    await waitFor(() => expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /stop/i })).not.toBeInTheDocument();
  });

  it("does not restore a stuck streaming bubble from a persisted transcript", async () => {
    window.localStorage.setItem(
      "pawpilot.chat.transcript.pet-1",
      JSON.stringify([
        {
          id: "u1",
          role: "user",
          text: "restored question",
          citations: [],
          emergency: false,
          streaming: false,
          errored: false,
        },
        {
          id: "a1",
          role: "assistant",
          text: "",
          citations: [],
          emergency: false,
          streaming: true,
          errored: false,
        },
      ]),
    );

    render(<ChatView pets={pets} />);

    await waitFor(() => expect(screen.getByText("restored question")).toBeInTheDocument());
    expect(screen.queryByText("Thinking…")).not.toBeInTheDocument();
  });

  it("passes a stable thread id across turns of the same conversation", async () => {
    streamMock.mockImplementation(() => scripted([{ type: "final", citations: [], emergency: false, tool_calls: [] }]));
    const user = userEvent.setup();
    render(<ChatView pets={pets} />);

    const input = screen.getByRole("textbox", { name: /ask pawpilot/i });
    await user.type(input, "first");
    await user.click(screen.getByRole("button", { name: /send/i }));
    await waitFor(() => expect(streamMock).toHaveBeenCalledTimes(1));
    await user.type(input, "second");
    await user.click(screen.getByRole("button", { name: /send/i }));
    await waitFor(() => expect(streamMock).toHaveBeenCalledTimes(2));

    const firstThread = (streamMock.mock.calls[0][0] as AgentAskInput).threadId;
    const secondThread = (streamMock.mock.calls[1][0] as AgentAskInput).threadId;
    expect(firstThread).toBeTruthy();
    expect(secondThread).toBe(firstThread);
  });
});
