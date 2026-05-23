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

  it("accepts a valid PNG file and surfaces the picked-photo label", async () => {
    const user = userEvent.setup();
    render(<ControlledHarness />);
    const file = new File(["pngbytes"], "luna.png", { type: "image/png" });
    await user.upload(screen.getByLabelText(/pet photo/i), file);
    expect(screen.getByText(/picked a new photo/i)).toBeInTheDocument();
  });

  it("rejects unsupported MIME types with an inline error", async () => {
    const user = userEvent.setup({ applyAccept: false });
    render(<ControlledHarness />);
    const heic = new File(["bytes"], "luna.heic", { type: "image/heic" });
    await user.upload(screen.getByLabelText(/pet photo/i), heic);
    expect(screen.getByRole("alert")).toHaveTextContent(/png, jpg, or webp/i);
  });

  it("rejects files over 5 MB with an inline error", async () => {
    const user = userEvent.setup();
    render(<ControlledHarness />);
    const big = new File([new Uint8Array(5 * 1024 * 1024 + 1)], "big.jpg", {
      type: "image/jpeg",
    });
    await user.upload(screen.getByLabelText(/pet photo/i), big);
    expect(screen.getByRole("alert")).toHaveTextContent(/5 mb or smaller/i);
  });

  it("offers a 'Remove current photo' control only when both existing photo and callback exist", () => {
    render(
      <ControlledHarness initialExisting="https://media/luna.jpg" withRemove />,
    );
    expect(
      screen.getByRole("button", { name: /remove current photo/i }),
    ).toBeInTheDocument();
  });

  it("hides the existing preview after the remove-existing callback fires", async () => {
    const user = userEvent.setup();
    render(
      <ControlledHarness initialExisting="https://media/luna.jpg" withRemove />,
    );
    await user.click(screen.getByRole("button", { name: /remove current photo/i }));
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText(/no photo/i)).toBeInTheDocument();
  });

  it("does not show the remove-existing button while a new file is picked", async () => {
    const user = userEvent.setup();
    render(
      <ControlledHarness initialExisting="https://media/luna.jpg" withRemove />,
    );
    const file = new File(["a"], "n.jpg", { type: "image/jpeg" });
    await user.upload(screen.getByLabelText(/pet photo/i), file);
    expect(
      screen.queryByRole("button", { name: /remove current photo/i }),
    ).not.toBeInTheDocument();
  });
});
