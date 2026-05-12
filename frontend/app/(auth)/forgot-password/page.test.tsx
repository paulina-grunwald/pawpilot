import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import ForgotPasswordPage from "./page";
import { getApiBaseUrl } from "@/lib/auth";

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("ForgotPasswordPage", () => {
  it("shows 'Email is required' on empty submit", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);
    await user.click(screen.getByRole("button", { name: /send reset link/i }));
    expect(await screen.findByText("Email is required")).toBeInTheDocument();
  });

  it("shows 'Enter a valid email address' for malformed email", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);
    await user.type(screen.getByLabelText(/email/i), "garbage");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));
    expect(
      await screen.findByText("Enter a valid email address"),
    ).toBeInTheDocument();
  });

  it("shows confirmation panel after successful submission, regardless of whether the email exists", async () => {
    server.use(
      http.post(`${getApiBaseUrl()}/auth/forgot-password`, () =>
        new HttpResponse(null, { status: 202 }),
      ),
    );
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);
    await user.type(screen.getByLabelText(/email/i), "anyone@b.co");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));
    expect(
      await screen.findByText(/if an account exists for anyone@b\.co/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /back to login/i }),
    ).toHaveAttribute("href", "/login");
    expect(screen.getByRole("button", { name: /resend/i })).toBeInTheDocument();
  });

  it("still shows the confirmation when the backend errors (no enumeration leak)", async () => {
    server.use(
      http.post(`${getApiBaseUrl()}/auth/forgot-password`, () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);
    await user.type(screen.getByLabelText(/email/i), "user@b.co");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));
    expect(
      await screen.findByText(/if an account exists for user@b\.co/i),
    ).toBeInTheDocument();
  });

  it("re-calls forgotPassword when 'Resend' is clicked", async () => {
    let calls = 0;
    server.use(
      http.post(`${getApiBaseUrl()}/auth/forgot-password`, () => {
        calls += 1;
        return new HttpResponse(null, { status: 202 });
      }),
    );
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);
    await user.type(screen.getByLabelText(/email/i), "x@b.co");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));
    const resendButton = await screen.findByRole("button", { name: /resend/i });
    await user.click(resendButton);
    await waitFor(() => expect(calls).toBe(2));
  });
});
