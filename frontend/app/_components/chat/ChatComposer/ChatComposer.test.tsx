import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatComposer } from "./ChatComposer";

describe("ChatComposer", () => {
  it("sends the trimmed query on Enter and clears the input", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatComposer onSend={onSend} onStop={() => {}} streaming={false} disabled={false} />);

    const input = screen.getByRole("textbox", { name: /ask pawpilot/i });
    await user.type(input, "  How much exercise?  ");
    await user.keyboard("{Enter}");

    expect(onSend).toHaveBeenCalledWith("How much exercise?");
    expect(input).toHaveValue("");
  });

  it("does not send a blank query", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatComposer onSend={onSend} onStop={() => {}} streaming={false} disabled={false} />);

    await user.type(screen.getByRole("textbox", { name: /ask pawpilot/i }), "   ");
    await user.keyboard("{Enter}");

    expect(onSend).not.toHaveBeenCalled();
  });

  it("keeps a newline on Shift+Enter", async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<ChatComposer onSend={onSend} onStop={() => {}} streaming={false} disabled={false} />);

    const input = screen.getByRole("textbox", { name: /ask pawpilot/i });
    await user.type(input, "line one{Shift>}{Enter}{/Shift}line two");

    expect(onSend).not.toHaveBeenCalled();
    expect(input).toHaveValue("line one\nline two");
  });

  it("shows a Stop button while streaming and calls onStop", async () => {
    const onStop = vi.fn();
    const user = userEvent.setup();
    render(<ChatComposer onSend={() => {}} onStop={onStop} streaming={true} disabled={true} />);

    expect(screen.queryByRole("button", { name: /send/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /stop/i }));
    expect(onStop).toHaveBeenCalled();
  });
});
