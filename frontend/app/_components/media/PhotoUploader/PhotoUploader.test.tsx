import { beforeAll, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { PhotoUploader } from "./PhotoUploader";

beforeAll(() => {
  if (typeof URL.createObjectURL !== "function") {
    URL.createObjectURL = vi.fn(() => "blob:mock");
  }
  if (typeof URL.revokeObjectURL !== "function") {
    URL.revokeObjectURL = vi.fn();
  }
});

function ControlledHarness({
  initialExisting = null,
  withRemove = false,
}: {
  initialExisting?: string | null;
  withRemove?: boolean;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [removeRequested, setRemoveRequested] = useState(false);
  return (
    <PhotoUploader
      existingPhotoUrl={initialExisting}
      file={file}
      removeRequested={removeRequested}
      onFileChange={setFile}
      onRemoveExisting={withRemove ? () => setRemoveRequested(true) : undefined}
    />
  );
}

describe("PhotoUploader", () => {
  it("renders a placeholder when no existing photo and no file is picked", () => {
    render(<ControlledHarness />);
    expect(screen.getByText(/no photo/i)).toBeInTheDocument();
  });

  it("renders the existing photo preview when an existingPhotoUrl is provided", () => {
    render(<ControlledHarness initialExisting="https://media/luna.jpg" />);
    const preview = screen.getByRole("img");
    expect(preview).toHaveAttribute("src", "https://media/luna.jpg");
  });

  it("does not show the upload modal by default", () => {
    render(<ControlledHarness initialExisting="https://media/luna.jpg" />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByText(/drop a photo here/i)).not.toBeInTheDocument();
  });

  it("labels the trigger 'Add photo' when there is no existing photo", () => {
    render(<ControlledHarness />);
    expect(screen.getByRole("button", { name: /add photo/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /change photo/i })).not.toBeInTheDocument();
  });

  it("labels the trigger 'Change photo' when an existing photo is shown", () => {
    render(<ControlledHarness initialExisting="https://media/luna.jpg" />);
    expect(screen.getByRole("button", { name: /change photo/i })).toBeInTheDocument();
  });

  it("opens the upload modal when the trigger is clicked", async () => {
    const user = userEvent.setup();
    render(<ControlledHarness initialExisting="https://media/luna.jpg" />);
    await user.click(screen.getByRole("button", { name: /change photo/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/drop a photo here/i)).toBeInTheDocument();
  });

  it("traps Tab focus within the upload modal", async () => {
    const user = userEvent.setup();
    render(<ControlledHarness />);
    await user.click(screen.getByRole("button", { name: /add photo/i }));
    const fileInput = screen.getByLabelText(/pet photo/i);
    const cancel = screen.getByRole("button", { name: /cancel/i });

    fileInput.focus();
    await user.tab();
    expect(cancel).toHaveFocus();
    // Wrap forward past the last focusable back to the first.
    await user.tab();
    expect(fileInput).toHaveFocus();
    // Wrap backward from the first to the last.
    await user.tab({ shift: true });
    expect(cancel).toHaveFocus();
  });

  it("closes the modal when 'Cancel' is clicked", async () => {
    const user = userEvent.setup();
    render(<ControlledHarness initialExisting="https://media/luna.jpg" />);
    await user.click(screen.getByRole("button", { name: /change photo/i }));
    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("closes the modal when Escape is pressed", async () => {
    const user = userEvent.setup();
    render(<ControlledHarness initialExisting="https://media/luna.jpg" />);
    await user.click(screen.getByRole("button", { name: /change photo/i }));
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("accepts a valid PNG file from the modal and closes it", async () => {
    const user = userEvent.setup();
    render(<ControlledHarness />);
    await user.click(screen.getByRole("button", { name: /add photo/i }));
    const file = new File(["pngbytes"], "luna.png", { type: "image/png" });
    await user.upload(screen.getByLabelText(/pet photo/i), file);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /discard pick/i })).toBeInTheDocument();
  });

  it("rejects unsupported MIME types with an inline error and keeps the modal open", async () => {
    const user = userEvent.setup({ applyAccept: false });
    render(<ControlledHarness />);
    await user.click(screen.getByRole("button", { name: /add photo/i }));
    const heic = new File(["bytes"], "luna.heic", { type: "image/heic" });
    await user.upload(screen.getByLabelText(/pet photo/i), heic);
    expect(screen.getByRole("alert")).toHaveTextContent(/png, jpg, or webp/i);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("rejects files over 5 MB with an inline error and keeps the modal open", async () => {
    const user = userEvent.setup();
    render(<ControlledHarness />);
    await user.click(screen.getByRole("button", { name: /add photo/i }));
    const big = new File([new Uint8Array(5 * 1024 * 1024 + 1)], "big.jpg", {
      type: "image/jpeg",
    });
    await user.upload(screen.getByLabelText(/pet photo/i), big);
    expect(screen.getByRole("alert")).toHaveTextContent(/5 mb or smaller/i);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("offers a 'Remove current photo' control only when both existing photo and callback exist", () => {
    render(<ControlledHarness initialExisting="https://media/luna.jpg" withRemove />);
    expect(screen.getByRole("button", { name: /remove current photo/i })).toBeInTheDocument();
  });

  it("hides the existing preview after the remove-existing callback fires", async () => {
    const user = userEvent.setup();
    render(<ControlledHarness initialExisting="https://media/luna.jpg" withRemove />);
    await user.click(screen.getByRole("button", { name: /remove current photo/i }));
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText(/no photo/i)).toBeInTheDocument();
  });

  it("does not show the remove-existing button while a new file is picked", async () => {
    const user = userEvent.setup();
    render(<ControlledHarness initialExisting="https://media/luna.jpg" withRemove />);
    await user.click(screen.getByRole("button", { name: /change photo/i }));
    const file = new File(["a"], "n.jpg", { type: "image/jpeg" });
    await user.upload(screen.getByLabelText(/pet photo/i), file);
    expect(screen.queryByRole("button", { name: /remove current photo/i })).not.toBeInTheDocument();
  });

  it("closes the modal when clicking the backdrop", async () => {
    const user = userEvent.setup();
    render(<ControlledHarness initialExisting="https://media/luna.jpg" />);
    await user.click(screen.getByRole("button", { name: /change photo/i }));
    const dialog = screen.getByRole("dialog");
    const backdrop = dialog.parentElement as HTMLElement;
    await user.pointer({ keys: "[MouseLeft>]", target: backdrop });
    await user.pointer({ keys: "[/MouseLeft]" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("clears a picked file when 'Discard pick' is clicked", async () => {
    const user = userEvent.setup();
    render(<ControlledHarness initialExisting="https://media/luna.jpg" withRemove />);
    await user.click(screen.getByRole("button", { name: /change photo/i }));
    const file = new File(["a"], "n.jpg", { type: "image/jpeg" });
    await user.upload(screen.getByLabelText(/pet photo/i), file);
    await user.click(screen.getByRole("button", { name: /discard pick/i }));
    expect(screen.queryByRole("button", { name: /discard pick/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /remove current photo/i })).toBeInTheDocument();
  });
});
