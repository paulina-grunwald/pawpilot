import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import LoginPage from "./page";
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

describe("LoginPage", () => {
  it("shows inline 'required' errors on empty submit and skips the network call", async () => {
    let called = false;
    server.use(
      http.post(`${getApiBaseUrl()}/auth/login`, () => {
        called = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    render(<LoginPage />);
    await user.click(screen.getByRole("button", { name: /log in/i }));
    expect(await screen.findByText("Email is required")).toBeInTheDocument();
    expect(screen.getByText("Password is required")).toBeInTheDocument();
    expect(called).toBe(false);
  });

  it("shows 'Enter a valid email address' for malformed input", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);
    await user.type(screen.getByLabelText(/email/i), "not-an-email");
    await user.type(screen.getByLabelText(/password/i), "anything");
    await user.click(screen.getByRole("button", { name: /log in/i }));
    expect(
      await screen.findByText("Enter a valid email address"),
    ).toBeInTheDocument();
  });

  it("redirects to /dashboard on 204", async () => {
    server.use(
      http.post(`${getApiBaseUrl()}/auth/login`, () =>
        new HttpResponse(null, { status: 204 }),
      ),
    );
    const user = userEvent.setup();
    render(<LoginPage />);
    await user.type(screen.getByLabelText(/email/i), "a@b.co");
    await user.type(screen.getByLabelText(/password/i), "password");
    await user.click(screen.getByRole("button", { name: /log in/i }));
    await waitFor(() => expect(replaceSpy).toHaveBeenCalledWith("/dashboard"));
    expect(refreshSpy).toHaveBeenCalled();
  });

  it("shows 'Incorrect email or password.' on LOGIN_BAD_CREDENTIALS", async () => {
    server.use(
      http.post(`${getApiBaseUrl()}/auth/login`, () =>
        HttpResponse.json({ detail: "LOGIN_BAD_CREDENTIALS" }, { status: 400 }),
      ),
    );
    const user = userEvent.setup();
    render(<LoginPage />);
    await user.type(screen.getByLabelText(/email/i), "a@b.co");
    await user.type(screen.getByLabelText(/password/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: /log in/i }));
    expect(
      await screen.findByText("Incorrect email or password."),
    ).toBeInTheDocument();
    expect(replaceSpy).not.toHaveBeenCalled();
  });

  it("shows network error copy when the request fails", async () => {
    server.use(
      http.post(`${getApiBaseUrl()}/auth/login`, () => HttpResponse.error()),
    );
    const user = userEvent.setup();
    render(<LoginPage />);
    await user.type(screen.getByLabelText(/email/i), "a@b.co");
    await user.type(screen.getByLabelText(/password/i), "password");
    await user.click(screen.getByRole("button", { name: /log in/i }));
    expect(
      await screen.findByText(/couldn't reach the server/i),
    ).toBeInTheDocument();
  });

  it("renders 'Create account' link to /signup and 'Forgot password?' to /forgot-password", () => {
    render(<LoginPage />);
    expect(screen.getByRole("link", { name: /create account/i })).toHaveAttribute(
      "href",
      "/signup",
    );
    expect(screen.getByRole("link", { name: /forgot password/i })).toHaveAttribute(
      "href",
      "/forgot-password",
    );
  });

  it("renders the password-reset-success flash banner when ?flash=password-reset-success", () => {
    mockSearchParams = new URLSearchParams("flash=password-reset-success");
    render(<LoginPage />);
    expect(screen.getByRole("status")).toHaveTextContent(/password updated/i);
  });
});
