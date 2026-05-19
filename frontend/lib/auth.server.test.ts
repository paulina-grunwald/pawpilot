import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { fetchCurrentUserFromBackend } from "./auth.server";
import { getApiBaseUrl } from "./auth";

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("fetchCurrentUserFromBackend", () => {
  it("returns null when no cookie header is provided (skips the request)", async () => {
    const user = await fetchCurrentUserFromBackend({ cookieHeader: null });
    expect(user).toBeNull();
  });

  it("forwards the cookie header to /users/me", async () => {
    let forwardedCookie: string | null = null;
    server.use(
      http.get(`${getApiBaseUrl()}/users/me`, ({ request }) => {
        forwardedCookie = request.headers.get("cookie");
        return HttpResponse.json({
          id: "u1",
          email: "a@b.co",
          is_active: true,
          is_verified: false,
          created_at: "2026-01-01T00:00:00Z",
        });
      }),
    );
    const user = await fetchCurrentUserFromBackend({
      cookieHeader: "pawpilot_auth=tok",
    });
    expect(forwardedCookie).toBe("pawpilot_auth=tok");
    expect(user?.email).toBe("a@b.co");
  });

  it("returns null on 401", async () => {
    server.use(
      http.get(`${getApiBaseUrl()}/users/me`, () =>
        HttpResponse.json({ detail: "Unauthorized" }, { status: 401 }),
      ),
    );
    const user = await fetchCurrentUserFromBackend({
      cookieHeader: "pawpilot_auth=stale",
    });
    expect(user).toBeNull();
  });

  it("throws on other backend failures", async () => {
    server.use(
      http.get(`${getApiBaseUrl()}/users/me`, () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );
    await expect(
      fetchCurrentUserFromBackend({ cookieHeader: "pawpilot_auth=tok" }),
    ).rejects.toThrow(/500/);
  });
});
