import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import ResetPasswordPage from "./page";
import { getApiBaseUrl } from "@/lib/auth";

const replaceSpy = vi.fn();
const refreshSpy = vi.fn();
let mockSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceSpy, refresh: refreshSpy }),
  useSearchParams: () => mockSearchParams,
}));

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  replaceSpy.mockClear();
  refreshSpy.mockClear();
  mockSearchParams = new URLSearchParams();
});
afterAll(() => server.close());

describe("ResetPasswordPage", () => {
  it("renders the 'invalid link' screen when there is no token in the URL", () => {
    render(<ResetPasswordPage />);
    expect(
      screen.getByText(/this reset link is invalid or expired/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /request a new link/i }),
    ).toHaveAttribute("href", "/forgot-password");
  });

  it("shows 'Password is required' on empty submit", async () => {
    mockSearchParams = new URLSearchParams("token=tok");
    const user = userEvent.setup();
    render(<ResetPasswordPage />);
    await user.click(screen.getByRole("button", { name: /update password/i }));
    expect(await screen.findByText("Password is required")).toBeInTheDocument();
  });

  it("shows 'Password must be at least 8 characters' for short input", async () => {
    mockSearchParams = new URLSearchParams("token=tok");
    const user = userEvent.setup();
    render(<ResetPasswordPage />);
    await user.type(screen.getByLabelText(/^new password/i), "short");
    await user.type(screen.getByLabelText(/confirm/i), "short");
    await user.click(screen.getByRole("button", { name: /update password/i }));
    expect(
      await screen.findByText("Password must be at least 8 characters"),
    ).toBeInTheDocument();
  });

  it("shows 'Passwords don't match' when the two fields differ", async () => {
    mockSearchParams = new URLSearchParams("token=tok");
    const user = userEvent.setup();
    render(<ResetPasswordPage />);
    await user.type(screen.getByLabelText(/^new password/i), "12345678");
    await user.type(screen.getByLabelText(/confirm/i), "12345679");
    await user.click(screen.getByRole("button", { name: /update password/i }));
    expect(
      await screen.findByText("Passwords don't match"),
    ).toBeInTheDocument();
  });

  it("redirects to /login?flash=password-reset-success on success", async () => {
    mockSearchParams = new URLSearchParams("token=tok");
    server.use(
      http.post(`${getApiBaseUrl()}/auth/reset-password`, () =>
        HttpResponse.json({}, { status: 200 }),
      ),
    );
    const user = userEvent.setup();
    render(<ResetPasswordPage />);
    await user.type(screen.getByLabelText(/^new password/i), "12345678");
    await user.type(screen.getByLabelText(/confirm/i), "12345678");
    await user.click(screen.getByRole("button", { name: /update password/i }));
    await waitFor(() =>
      expect(replaceSpy).toHaveBeenCalledWith(
        "/login?flash=password-reset-success",
      ),
    );
  });

  it("swaps to the 'expired link' panel when the backend returns RESET_PASSWORD_BAD_TOKEN", async () => {
    mockSearchParams = new URLSearchParams("token=bad");
    server.use(
      http.post(`${getApiBaseUrl()}/auth/reset-password`, () =>
        HttpResponse.json(
          { detail: "RESET_PASSWORD_BAD_TOKEN" },
          { status: 400 },
        ),
      ),
    );
    const user = userEvent.setup();
    render(<ResetPasswordPage />);
    await user.type(screen.getByLabelText(/^new password/i), "12345678");
    await user.type(screen.getByLabelText(/confirm/i), "12345678");
    await user.click(screen.getByRole("button", { name: /update password/i }));
    expect(
      await screen.findByText(/this reset link is invalid or has expired/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /request a new link/i }),
    ).toHaveAttribute("href", "/forgot-password");
  });

  it("shows inline password error when backend returns RESET_PASSWORD_INVALID_PASSWORD", async () => {
    mockSearchParams = new URLSearchParams("token=tok");
    server.use(
      http.post(`${getApiBaseUrl()}/auth/reset-password`, () =>
        HttpResponse.json(
          {
            detail: {
              code: "RESET_PASSWORD_INVALID_PASSWORD",
              reason: "weak",
            },
          },
          { status: 400 },
        ),
      ),
    );
    const user = userEvent.setup();
    render(<ResetPasswordPage />);
    await user.type(screen.getByLabelText(/^new password/i), "12345678");
    await user.type(screen.getByLabelText(/confirm/i), "12345678");
    await user.click(screen.getByRole("button", { name: /update password/i }));
    expect(
      await screen.findByText(/your password doesn't meet the requirements/i),
    ).toBeInTheDocument();
  });
});
