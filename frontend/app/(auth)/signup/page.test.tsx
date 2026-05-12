import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import SignupPage from "./page";
import { getApiBaseUrl } from "@/lib/auth";

const replaceSpy = vi.fn();
const refreshSpy = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceSpy, refresh: refreshSpy }),
}));

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  replaceSpy.mockClear();
  refreshSpy.mockClear();
});
afterAll(() => server.close());

describe("SignupPage", () => {
  it("shows inline errors on empty submit", async () => {
    const user = userEvent.setup();
    render(<SignupPage />);
    await user.click(screen.getByRole("button", { name: /create account/i }));
    expect(await screen.findByText("Email is required")).toBeInTheDocument();
    expect(screen.getByText("Password is required")).toBeInTheDocument();
  });

  it("shows 'Password must be at least 8 characters' for short passwords", async () => {
    const user = userEvent.setup();
    render(<SignupPage />);
    await user.type(screen.getByLabelText(/email/i), "a@b.co");
    await user.type(screen.getByLabelText(/password/i), "short");
    await user.click(screen.getByRole("button", { name: /create account/i }));
    expect(
      await screen.findByText("Password must be at least 8 characters"),
    ).toBeInTheDocument();
  });

  it("auto-logs in and redirects to /dashboard on successful signup", async () => {
    let loginCalled = false;
    server.use(
      http.post(`${getApiBaseUrl()}/auth/register`, () =>
        HttpResponse.json(
          {
            id: "u1",
            email: "new@b.co",
            is_active: true,
            is_verified: false,
            created_at: "2026-01-01T00:00:00Z",
          },
          { status: 201 },
        ),
      ),
      http.post(`${getApiBaseUrl()}/auth/login`, () => {
        loginCalled = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    render(<SignupPage />);
    await user.type(screen.getByLabelText(/email/i), "new@b.co");
    await user.type(screen.getByLabelText(/^password/i), "12345678");
    await user.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() => expect(replaceSpy).toHaveBeenCalledWith("/dashboard"));
    expect(loginCalled).toBe(true);
  });

  it("surfaces a friendly message with login link when the email already exists", async () => {
    server.use(
      http.post(`${getApiBaseUrl()}/auth/register`, () =>
        HttpResponse.json(
          { detail: "REGISTER_USER_ALREADY_EXISTS" },
          { status: 400 },
        ),
      ),
    );
    const user = userEvent.setup();
    render(<SignupPage />);
    await user.type(screen.getByLabelText(/email/i), "taken@b.co");
    await user.type(screen.getByLabelText(/^password/i), "12345678");
    await user.click(screen.getByRole("button", { name: /create account/i }));
    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(/already exists/i);
    expect(
      screen.getByRole("link", { name: /log in instead/i }),
    ).toHaveAttribute("href", "/login");
  });

  it("falls back to generic error on unknown backend failures", async () => {
    server.use(
      http.post(`${getApiBaseUrl()}/auth/register`, () =>
        HttpResponse.json({ detail: "BOOM" }, { status: 500 }),
      ),
    );
    const user = userEvent.setup();
    render(<SignupPage />);
    await user.type(screen.getByLabelText(/email/i), "a@b.co");
    await user.type(screen.getByLabelText(/^password/i), "12345678");
    await user.click(screen.getByRole("button", { name: /create account/i }));
    expect(
      await screen.findByText(/something went wrong/i),
    ).toBeInTheDocument();
  });

  it("renders 'Log in' footer link to /login", () => {
    render(<SignupPage />);
    expect(screen.getByRole("link", { name: /^log in$/i })).toHaveAttribute(
      "href",
      "/login",
    );
  });
});
