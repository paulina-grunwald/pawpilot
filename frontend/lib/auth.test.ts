import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { AuthError, getApiBaseUrl, getCurrentUser, login, logout, signup } from "./auth";

const API_BASE_URL = getApiBaseUrl();

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("signup", () => {
  it("returns the created user on 201", async () => {
    server.use(
      http.post(`${API_BASE_URL}/auth/register`, async () =>
        HttpResponse.json(
          {
            id: "user-id",
            email: "a@b.co",
            is_active: true,
            is_verified: false,
            created_at: "2026-01-01T00:00:00Z",
          },
          { status: 201 },
        ),
      ),
    );
    const user = await signup({ email: "a@b.co", password: "12345678" });
    expect(user.email).toBe("a@b.co");
  });

  it("throws AuthError with REGISTER_USER_ALREADY_EXISTS when backend returns that code", async () => {
    server.use(
      http.post(`${API_BASE_URL}/auth/register`, () =>
        HttpResponse.json({ detail: "REGISTER_USER_ALREADY_EXISTS" }, { status: 400 }),
      ),
    );
    await expect(signup({ email: "taken@b.co", password: "12345678" })).rejects.toMatchObject({
      name: "AuthError",
      code: "REGISTER_USER_ALREADY_EXISTS",
    });
  });

  it("throws AuthError with REGISTER_INVALID_PASSWORD when detail is an object", async () => {
    server.use(
      http.post(`${API_BASE_URL}/auth/register`, () =>
        HttpResponse.json(
          {
            detail: {
              code: "REGISTER_INVALID_PASSWORD",
              reason: "Password too short",
            },
          },
          { status: 400 },
        ),
      ),
    );
    await expect(signup({ email: "a@b.co", password: "12345678" })).rejects.toMatchObject({
      code: "REGISTER_INVALID_PASSWORD",
    });
  });

  it("throws AuthError with UNKNOWN for unexpected error shape", async () => {
    server.use(
      http.post(`${API_BASE_URL}/auth/register`, () =>
        HttpResponse.json({ weird: true }, { status: 500 }),
      ),
    );
    await expect(signup({ email: "a@b.co", password: "12345678" })).rejects.toMatchObject({
      code: "UNKNOWN",
    });
  });

  it("throws AuthError with VALIDATION_ERROR on 422", async () => {
    server.use(
      http.post(`${API_BASE_URL}/auth/register`, () =>
        HttpResponse.json({ detail: [] }, { status: 422 }),
      ),
    );
    await expect(signup({ email: "a@b.co", password: "12345678" })).rejects.toMatchObject({
      code: "VALIDATION_ERROR",
    });
  });
});

describe("login", () => {
  it("submits form-encoded body with username + password and resolves on 204", async () => {
    let capturedBody = "";
    let capturedContentType: string | null = null;
    server.use(
      http.post(`${API_BASE_URL}/auth/login`, async ({ request }) => {
        capturedBody = await request.text();
        capturedContentType = request.headers.get("content-type");
        return new HttpResponse(null, { status: 204 });
      }),
    );
    await login({ email: "a@b.co", password: "secret123" });
    expect(capturedContentType).toContain("application/x-www-form-urlencoded");
    const parsed = new URLSearchParams(capturedBody);
    expect(parsed.get("username")).toBe("a@b.co");
    expect(parsed.get("password")).toBe("secret123");
  });

  it("throws AuthError with LOGIN_BAD_CREDENTIALS on 400", async () => {
    server.use(
      http.post(`${API_BASE_URL}/auth/login`, () =>
        HttpResponse.json({ detail: "LOGIN_BAD_CREDENTIALS" }, { status: 400 }),
      ),
    );
    await expect(login({ email: "a@b.co", password: "wrong" })).rejects.toMatchObject({
      code: "LOGIN_BAD_CREDENTIALS",
    });
  });

  it("throws NETWORK_ERROR when fetch rejects", async () => {
    const failingFetch = (() => Promise.reject(new TypeError("Network failed"))) as typeof fetch;
    await expect(
      login({ email: "a@b.co", password: "secret123" }, failingFetch),
    ).rejects.toMatchObject({ code: "NETWORK_ERROR" });
  });
});

describe("logout", () => {
  it("POSTs /auth/logout and resolves on 204", async () => {
    let called = false;
    server.use(
      http.post(`${API_BASE_URL}/auth/logout`, () => {
        called = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    await logout();
    expect(called).toBe(true);
  });
});

describe("getCurrentUser", () => {
  it("returns the user on 200", async () => {
    server.use(
      http.get(`${API_BASE_URL}/users/me`, () =>
        HttpResponse.json({
          id: "u1",
          email: "a@b.co",
          is_active: true,
          is_verified: false,
          created_at: "2026-01-01T00:00:00Z",
        }),
      ),
    );
    const user = await getCurrentUser();
    expect(user?.email).toBe("a@b.co");
  });

  it("returns null on 401", async () => {
    server.use(
      http.get(`${API_BASE_URL}/users/me`, () =>
        HttpResponse.json({ detail: "Unauthorized" }, { status: 401 }),
      ),
    );
    expect(await getCurrentUser()).toBeNull();
  });

  it("throws AuthError on other failures", async () => {
    server.use(
      http.get(`${API_BASE_URL}/users/me`, () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );
    await expect(getCurrentUser()).rejects.toBeInstanceOf(AuthError);
  });

  it("throws NETWORK_ERROR when fetch rejects", async () => {
    const failingFetch = (() => Promise.reject(new TypeError("offline"))) as typeof fetch;
    await expect(getCurrentUser(failingFetch)).rejects.toMatchObject({
      code: "NETWORK_ERROR",
    });
  });
});
