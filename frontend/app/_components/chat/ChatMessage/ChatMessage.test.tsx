import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { Citation } from "@/lib/agent";
import { ChatMessage, type ChatMessageModel } from "./ChatMessage";

function message(overrides: Partial<ChatMessageModel>): ChatMessageModel {
  return {
    id: "m1",
    role: "assistant",
    text: "",
    citations: [],
    emergency: false,
    streaming: false,
    errored: false,
    ...overrides,
  };
}

const citation: Citation = {
  ref: "S1",
  kind: "corpus",
  title: "WSAVA Guide",
  url: "https://example.org/a",
  source_id: null,
  source_tier: null,
  page_start: null,
};

describe("ChatMessage", () => {
  it("renders a user message", () => {
    render(<ChatMessage message={message({ role: "user", text: "Is chocolate bad?" })} />);
    expect(screen.getByText("Is chocolate bad?")).toBeInTheDocument();
  });

  it("renders assistant text with a citation link that opens in a new tab", () => {
    render(
      <ChatMessage message={message({ text: "Yes, avoid it [S1].", citations: [citation] })} />,
    );
    expect(screen.getByText("Yes, avoid it [S1].")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /wsava guide/i });
    expect(link).toHaveAttribute("href", "https://example.org/a");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("renders markdown bold as a <strong> element", () => {
    render(<ChatMessage message={message({ text: "You should **avoid chocolate**." })} />);
    const strong = screen.getByText("avoid chocolate");
    expect(strong.tagName).toBe("STRONG");
  });

  it("renders markdown bullet lists", () => {
    render(<ChatMessage message={message({ text: "Watch for:\n\n- vomiting\n- lethargy" })} />);
    expect(screen.getByText("vomiting").tagName).toBe("LI");
    expect(screen.getByRole("list")).toBeInTheDocument();
  });

  it("marks an emergency answer", () => {
    render(<ChatMessage message={message({ text: "Go to the vet now.", emergency: true })} />);
    expect(screen.getByText(/possibly urgent/i)).toBeInTheDocument();
  });

  it("shows a thinking state before the first token", () => {
    render(<ChatMessage message={message({ streaming: true, text: "" })} />);
    expect(screen.getByText(/thinking/i)).toBeInTheDocument();
  });
});
