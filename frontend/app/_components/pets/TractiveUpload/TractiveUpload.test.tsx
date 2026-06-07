import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { getApiBaseUrl } from "@/lib/auth";
import { TractiveUpload } from "./TractiveUpload";

const API = getApiBaseUrl();
const PET_ID = "pet-1";
const ENDPOINT = `${API}/pets/${PET_ID}/tractive/ingest`;

const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  refresh.mockReset();
});
afterAll(() => server.close());

function fakeZipFile(): File {
  return new File([new Uint8Array([0x50, 0x4b, 0x05, 0x06])], "export.zip", {
    type: "application/zip",
  });
}

describe("TractiveUpload", () => {
  it("renders the file input and a disabled upload button by default", () => {
    render(<TractiveUpload petId={PET_ID} />);
    expect(screen.getByLabelText(/tractive export zip/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /upload export/i })).toBeDisabled();
  });

  it("enables the upload button after a file is selected", async () => {
    const user = userEvent.setup();
    render(<TractiveUpload petId={PET_ID} />);
    await user.upload(screen.getByLabelText(/tractive export zip/i), fakeZipFile());
    expect(screen.getByRole("button", { name: /upload export/i })).toBeEnabled();
  });

  it("shows success summary and calls router.refresh after a 200", async () => {
    server.use(
      http.post(ENDPOINT, () =>
        HttpResponse.json({
          ingest_batch_id: "abc",
          rollups_upserted: 5,
          raw_payloads_stored: 5,
          date_range_start: "2024-05-01",
          date_range_end: "2024-05-05",
        }),
      ),
    );
    const user = userEvent.setup();
    render(<TractiveUpload petId={PET_ID} />);
    await user.upload(screen.getByLabelText(/tractive export zip/i), fakeZipFile());
    await user.click(screen.getByRole("button", { name: /upload export/i }));

    await waitFor(() =>
      expect(screen.getByText(/imported 5 days \(2024-05-01 – 2024-05-05\)/i)).toBeInTheDocument(),
    );
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: /upload another export/i })).toBeInTheDocument();
  });

  it("shows the invalid-zip error message on 400 TRACTIVE_INVALID_ZIP", async () => {
    server.use(
      http.post(ENDPOINT, () =>
        HttpResponse.json({ detail: "TRACTIVE_INVALID_ZIP: missing X" }, { status: 400 }),
      ),
    );
    const user = userEvent.setup();
    render(<TractiveUpload petId={PET_ID} />);
    await user.upload(screen.getByLabelText(/tractive export zip/i), fakeZipFile());
    await user.click(screen.getByRole("button", { name: /upload export/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/doesn't look like a tractive/i),
    );
    expect(refresh).not.toHaveBeenCalled();
  });

  it("shows the too-large error on 413", async () => {
    server.use(
      http.post(ENDPOINT, () =>
        HttpResponse.json({ detail: "TRACTIVE_UPLOAD_TOO_LARGE" }, { status: 413 }),
      ),
    );
    const user = userEvent.setup();
    render(<TractiveUpload petId={PET_ID} />);
    await user.upload(screen.getByLabelText(/tractive export zip/i), fakeZipFile());
    await user.click(screen.getByRole("button", { name: /upload export/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/upload is too large/i),
    );
  });

  it("returns to idle state when the user clicks 'Upload another export'", async () => {
    server.use(
      http.post(ENDPOINT, () =>
        HttpResponse.json({
          ingest_batch_id: "abc",
          rollups_upserted: 1,
          raw_payloads_stored: 5,
          date_range_start: "2024-05-01",
          date_range_end: "2024-05-01",
        }),
      ),
    );
    const user = userEvent.setup();
    render(<TractiveUpload petId={PET_ID} />);
    await user.upload(screen.getByLabelText(/tractive export zip/i), fakeZipFile());
    await user.click(screen.getByRole("button", { name: /upload export/i }));

    await user.click(await screen.findByRole("button", { name: /upload another export/i }));
    expect(screen.getByRole("button", { name: /upload export/i })).toBeDisabled();
  });
});
