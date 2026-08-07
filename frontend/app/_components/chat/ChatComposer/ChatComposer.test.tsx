import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatComposer } from "./ChatComposer";

const LINE_HEIGHT = 24;
const CHARACTERS_PER_LINE = 20;

function measuredLineCount(value: string): number {
  return value
    .split("\n")
    .reduce((total, line) => total + Math.max(Math.ceil(line.length / CHARACTERS_PER_LINE), 1), 0);
}

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

describe("ChatComposer auto-grow", () => {
  beforeEach(() => {
    Object.defineProperty(HTMLTextAreaElement.prototype, "scrollHeight", {
      configurable: true,
      get(this: HTMLTextAreaElement) {
        return measuredLineCount(this.value) * LINE_HEIGHT;
      },
    });
  });

  afterEach(() => {
    Reflect.deleteProperty(HTMLTextAreaElement.prototype, "scrollHeight");
  });

  it("starts at a single line", () => {
    render(<ChatComposer onSend={() => {}} onStop={() => {}} streaming={false} disabled={false} />);

    const input = screen.getByRole("textbox", { name: /ask pawpilot/i });
    expect(input.style.height).toBe("24px");
    expect(input.style.overflowY).toBe("hidden");
  });

  it("grows as the question wraps onto more lines", async () => {
    const user = userEvent.setup();
    render(<ChatComposer onSend={() => {}} onStop={() => {}} streaming={false} disabled={false} />);

    const input = screen.getByRole("textbox", { name: /ask pawpilot/i });
    await user.type(input, "a".repeat(55));

    expect(input.style.height).toBe("72px");
    expect(input.style.overflowY).toBe("hidden");
  });

  it("stops growing at the cap and scrolls instead", async () => {
    const user = userEvent.setup();
    render(<ChatComposer onSend={() => {}} onStop={() => {}} streaming={false} disabled={false} />);

    const input = screen.getByRole("textbox", { name: /ask pawpilot/i });
    await user.type(input, "a".repeat(200));

    expect(input.style.height).toBe("160px");
    expect(input.style.overflowY).toBe("auto");
  });

  it("shrinks back to a single line after sending", async () => {
    const user = userEvent.setup();
    render(<ChatComposer onSend={() => {}} onStop={() => {}} streaming={false} disabled={false} />);

    const input = screen.getByRole("textbox", { name: /ask pawpilot/i });
    await user.type(input, "a".repeat(80));
    expect(input.style.height).not.toBe("24px");

    await user.keyboard("{Enter}");

    expect(input.style.height).toBe("24px");
    expect(input.style.overflowY).toBe("hidden");
  });
});
