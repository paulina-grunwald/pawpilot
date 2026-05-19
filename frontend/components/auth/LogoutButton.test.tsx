import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { LogoutButton } from "./LogoutButton";
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

describe("LogoutButton", () => {
  it("calls /auth/logout and redirects to /login on success", async () => {
    let called = false;
    server.use(
      http.post(`${getApiBaseUrl()}/auth/logout`, () => {
        called = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    render(<LogoutButton />);
    await user.click(screen.getByRole("button", { name: /log out/i }));
    await waitFor(() => expect(called).toBe(true));
    await waitFor(() => expect(replaceSpy).toHaveBeenCalledWith("/login"));
    expect(refreshSpy).toHaveBeenCalled();
  });

  it("still redirects even if the backend returns an auth error", async () => {
    server.use(
      http.post(`${getApiBaseUrl()}/auth/logout`, () =>
        HttpResponse.json({ detail: "Unauthorized" }, { status: 401 }),
      ),
    );
    const user = userEvent.setup();
    render(<LogoutButton />);
    await user.click(screen.getByRole("button", { name: /log out/i }));
    await waitFor(() => expect(replaceSpy).toHaveBeenCalledWith("/login"));
  });

  it("surfaces an inline error and does not redirect on 500", async () => {
    server.use(
      http.post(`${getApiBaseUrl()}/auth/logout`, () =>
        HttpResponse.json({ detail: "Boom" }, { status: 500 }),
      ),
    );
    const user = userEvent.setup();
    render(<LogoutButton />);
    await user.click(screen.getByRole("button", { name: /log out/i }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/could not log out/i),
    );
    expect(replaceSpy).not.toHaveBeenCalled();
    expect(
      screen.getByRole("button", { name: /log out/i }),
    ).not.toBeDisabled();
  });

  it("surfaces an inline error on network failure", async () => {
    server.use(
      http.post(`${getApiBaseUrl()}/auth/logout`, () => HttpResponse.error()),
    );
    const user = userEvent.setup();
    render(<LogoutButton />);
    await user.click(screen.getByRole("button", { name: /log out/i }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/could not log out/i),
    );
    expect(replaceSpy).not.toHaveBeenCalled();
  });

  it("shows a loading label while logging out", async () => {
    server.use(
      http.post(
        `${getApiBaseUrl()}/auth/logout`,
        async () => {
          await new Promise((resolve) => setTimeout(resolve, 50));
          return new HttpResponse(null, { status: 204 });
        },
      ),
    );
    const user = userEvent.setup();
    render(<LogoutButton />);
    await user.click(screen.getByRole("button"));
    expect(
      await screen.findByRole("button", { name: /logging out/i }),
    ).toBeDisabled();
  });
});
