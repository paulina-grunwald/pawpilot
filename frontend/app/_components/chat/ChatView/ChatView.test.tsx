import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { activePetStorageKey } from "@/lib/activePet";
import type { AgentAskInput, AgentStreamEvent } from "@/lib/agent";
import { ChatView } from "./ChatView";

const { streamMock, pathnameMock, listThreadsMock, getThreadMock } = vi.hoisted(() => ({
  streamMock: vi.fn(),
  pathnameMock: vi.fn<() => string>(() => "/chat"),
  listThreadsMock: vi.fn(),
  getThreadMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({ usePathname: () => pathnameMock() }));
vi.mock("@/lib/agent", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/agent")>();
  return {
    ...actual,
    streamAgentAnswer: streamMock,
    listThreads: listThreadsMock,
    getThread: getThreadMock,
  };
});

async function* scripted(events: AgentStreamEvent[]): AsyncGenerator<AgentStreamEvent> {
  for (const event of events) yield event;
}

const pets = [{ id: "pet-1", name: "Luna", breed: "Aussie" }];
const USER_ID = "user-1";

afterEach(() => {
  streamMock.mockReset();
  listThreadsMock.mockReset();
  getThreadMock.mockReset();
  pathnameMock.mockReturnValue("/chat");
  window.localStorage.clear();
});

describe("ChatView", () => {
  it("shows the empty state before any message", () => {
    render(<ChatView pets={pets} userId={USER_ID} />);
    expect(screen.getByText("Ask anything about Luna.")).toBeInTheDocument();
  });

  it("defaults to the dog the user last focused instead of the first pet", async () => {
    window.localStorage.setItem(activePetStorageKey(USER_ID), "pet-2");
    const twoPets = [...pets, { id: "pet-2", name: "Rex", breed: "Beagle" }];
    render(<ChatView pets={twoPets} userId={USER_ID} />);
    expect(await screen.findByText("Ask anything about Rex.")).toBeInTheDocument();
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
    render(<ChatView pets={pets} userId={USER_ID} />);

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
    render(<ChatView pets={pets} userId={USER_ID} />);

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

    render(<ChatView pets={pets} userId={USER_ID} />);

    await waitFor(() => expect(screen.getByText("restored question")).toBeInTheDocument());
    expect(screen.queryByText("Thinking…")).not.toBeInTheDocument();
  });

  it("opens history and reopens a past conversation", async () => {
    listThreadsMock.mockResolvedValue([
      {
        thread_id: "conv-1",
        pet_id: "pet-1",
        title: "Feeding schedule",
        created_at: "2026-07-10T00:00:00Z",
        updated_at: "2026-07-11T00:00:00Z",
      },
    ]);
    getThreadMock.mockResolvedValue({
      thread_id: "conv-1",
      pet_id: "pet-1",
      title: "Feeding schedule",
      messages: [
        { role: "user", text: "How often?" },
        { role: "assistant", text: "Twice a day." },
      ],
    });
    const user = userEvent.setup();
    render(<ChatView pets={pets} userId={USER_ID} />);

    await user.click(screen.getByRole("button", { name: /^history$/i }));
    expect(await screen.findByText("Feeding schedule")).toBeInTheDocument();
    expect(listThreadsMock).toHaveBeenCalledWith("pet-1");

    await user.click(screen.getByRole("button", { name: /feeding schedule/i }));
    expect(await screen.findByText("Twice a day.")).toBeInTheDocument();
    expect(screen.getByText("How often?")).toBeInTheDocument();
    expect(getThreadMock).toHaveBeenCalledWith("conv-1");
  });

  it("passes a stable thread id across turns of the same conversation", async () => {
    streamMock.mockImplementation(() => scripted([{ type: "final", citations: [], emergency: false, tool_calls: [] }]));
    const user = userEvent.setup();
    render(<ChatView pets={pets} userId={USER_ID} />);

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
