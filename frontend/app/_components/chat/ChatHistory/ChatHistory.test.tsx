import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AgentThreadSummary } from "@/lib/agent";
import { ChatHistory } from "./ChatHistory";

const threads: AgentThreadSummary[] = [
  {
    thread_id: "t1",
    pet_id: "pet-1",
    title: "How much to feed?",
    created_at: "2026-07-10T00:00:00Z",
    updated_at: "2026-07-11T00:00:00Z",
  },
  {
    thread_id: "t2",
    pet_id: "pet-1",
    title: null,
    created_at: "2026-07-09T00:00:00Z",
    updated_at: "2026-07-09T00:00:00Z",
  },
];

const noop = () => {};

describe("ChatHistory", () => {
  it("lists conversations, falling back to a placeholder title", () => {
    render(
      <ChatHistory
        threads={threads}
        activeThreadId="t1"
        loading={false}
        onSelect={noop}
        onNewConversation={noop}
      />,
    );
    expect(screen.getByText("How much to feed?")).toBeInTheDocument();
    expect(screen.getByText("Untitled conversation")).toBeInTheDocument();
  });

  it("marks the active conversation", () => {
    render(
      <ChatHistory
        threads={threads}
        activeThreadId="t1"
        loading={false}
        onSelect={noop}
        onNewConversation={noop}
      />,
    );
    expect(screen.getByRole("button", { name: /how much to feed/i })).toHaveAttribute(
      "aria-current",
      "true",
    );
  });

  it("calls onSelect with the conversation's thread id", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(
      <ChatHistory
        threads={threads}
        activeThreadId={null}
        loading={false}
        onSelect={onSelect}
        onNewConversation={noop}
      />,
    );
    await user.click(screen.getByRole("button", { name: /how much to feed/i }));
    expect(onSelect).toHaveBeenCalledWith("t1");
  });

  it("shows the loading then empty states", () => {
    const { rerender } = render(
      <ChatHistory
        threads={[]}
        activeThreadId={null}
        loading
        onSelect={noop}
        onNewConversation={noop}
      />,
    );
    expect(screen.getByText("Loading…")).toBeInTheDocument();

    rerender(
      <ChatHistory
        threads={[]}
        activeThreadId={null}
        loading={false}
        onSelect={noop}
        onNewConversation={noop}
      />,
    );
    expect(screen.getByText("No past conversations yet.")).toBeInTheDocument();
  });

  it("triggers a new conversation", async () => {
    const onNewConversation = vi.fn();
    const user = userEvent.setup();
    render(
      <ChatHistory
        threads={threads}
        activeThreadId={null}
        loading={false}
        onSelect={noop}
        onNewConversation={onNewConversation}
      />,
    );
    await user.click(screen.getByRole("button", { name: /new conversation/i }));
    expect(onNewConversation).toHaveBeenCalled();
  });
});
