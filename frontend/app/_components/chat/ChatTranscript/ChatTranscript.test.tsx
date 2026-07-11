import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ChatMessageModel } from "../ChatMessage";
import { ChatTranscript } from "./ChatTranscript";

const assistantMessage: ChatMessageModel = {
  id: "message-1",
  role: "assistant",
  text: "Aussies are active.",
  citations: [],
  emergency: false,
  streaming: false,
  errored: false,
};

describe("ChatTranscript", () => {
  it("renders the empty state when there are no messages", () => {
    render(<ChatTranscript messages={[]} className="transcript" emptyState={<p>Nothing yet</p>} />);
    expect(screen.getByText("Nothing yet")).toBeInTheDocument();
  });

  it("renders the messages and hides the empty state once populated", () => {
    render(
      <ChatTranscript
        messages={[assistantMessage]}
        className="transcript"
        emptyState={<p>Nothing yet</p>}
      />,
    );
    expect(screen.getByText("Aussies are active.")).toBeInTheDocument();
    expect(screen.queryByText("Nothing yet")).not.toBeInTheDocument();
  });
});
