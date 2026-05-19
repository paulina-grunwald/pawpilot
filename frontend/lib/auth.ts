import type { LoginInput, SignupInput } from "./auth.schemas";

export type UserRead = {
  id: string;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
};

export type AuthErrorCode =
  | "REGISTER_USER_ALREADY_EXISTS"
  | "REGISTER_INVALID_PASSWORD"
  | "LOGIN_BAD_CREDENTIALS"
  | "LOGIN_USER_NOT_VERIFIED"
  | "VALIDATION_ERROR"
  | "NETWORK_ERROR"
  | "UNKNOWN";

export class AuthError extends Error {
  readonly code: AuthErrorCode;
  readonly status?: number;

  constructor(code: AuthErrorCode, message: string, status?: number) {
    super(message);
    this.code = code;
    this.status = status;
    this.name = "AuthError";
  }
}

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

type FetchFn = typeof fetch;

const KNOWN_AUTH_ERROR_CODES: ReadonlySet<AuthErrorCode> = new Set([
  "REGISTER_USER_ALREADY_EXISTS",
  "REGISTER_INVALID_PASSWORD",
  "LOGIN_BAD_CREDENTIALS",
  "LOGIN_USER_NOT_VERIFIED",
  "VALIDATION_ERROR",
  "NETWORK_ERROR",
  "UNKNOWN",
]);

function coerceErrorCode(raw: unknown): AuthErrorCode {
  if (typeof raw === "string" && KNOWN_AUTH_ERROR_CODES.has(raw as AuthErrorCode)) {
    return raw as AuthErrorCode;
  }
  return "UNKNOWN";
}

async function parseErrorCode(response: Response): Promise<AuthErrorCode> {
  if (response.status === 422) return "VALIDATION_ERROR";
  try {
    const body = (await response.clone().json()) as { detail?: unknown };
    if (typeof body.detail === "string") {
      return coerceErrorCode(body.detail);
    }
    if (
      body.detail &&
      typeof body.detail === "object" &&
      "code" in body.detail
    ) {
      return coerceErrorCode((body.detail as { code: unknown }).code);
    }
  } catch {
    /* fall through */
  }
  return "UNKNOWN";
}

async function authRequest<TBody, TResult>(
  input: {
    path: string;
    method?: "GET" | "POST";
    body?: TBody;
    form?: URLSearchParams;
    parse: (response: Response) => Promise<TResult>;
    fetchImpl?: FetchFn;
  },
): Promise<TResult> {
  const { path, method = "POST", body, form, parse } = input;
  const fetchImpl = input.fetchImpl ?? fetch;
  let response: Response;
  try {
    response = await fetchImpl(`${getApiBaseUrl()}${path}`, {
      method,
      credentials: "include",
      headers: form
        ? { "Content-Type": "application/x-www-form-urlencoded" }
        : body !== undefined
          ? { "Content-Type": "application/json" }
          : {},
      body: form ? form.toString() : body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (caught) {
    throw new AuthError(
      "NETWORK_ERROR",
      caught instanceof Error ? caught.message : String(caught),
    );
  }
  if (!response.ok) {
    const code = await parseErrorCode(response);
    throw new AuthError(
      code,
      `Request to ${path} failed with ${response.status}`,
      response.status,
    );
  }
  return parse(response);
}

export async function signup(
  input: SignupInput,
  fetchImpl?: FetchFn,
): Promise<UserRead> {
  return authRequest<SignupInput, UserRead>({
    path: "/auth/register",
    body: input,
    parse: (response) => response.json() as Promise<UserRead>,
    fetchImpl,
  });
}

export async function login(
  input: LoginInput,
  fetchImpl?: FetchFn,
): Promise<void> {
  const form = new URLSearchParams();
  form.set("username", input.email);
  form.set("password", input.password);
  await authRequest<undefined, void>({
    path: "/auth/login",
    form,
    parse: async () => undefined,
    fetchImpl,
  });
}

export async function logout(fetchImpl?: FetchFn): Promise<void> {
  await authRequest<undefined, void>({
    path: "/auth/logout",
    parse: async () => undefined,
    fetchImpl,
  });
}

export async function getCurrentUser(
  fetchImpl?: FetchFn,
): Promise<UserRead | null> {
  const fetchToUse = fetchImpl ?? fetch;
  let response: Response;
  try {
    response = await fetchToUse(`${getApiBaseUrl()}/users/me`, {
      credentials: "include",
    });
  } catch (caught) {
    throw new AuthError(
      "NETWORK_ERROR",
      caught instanceof Error ? caught.message : String(caught),
    );
  }
  if (response.status === 401) return null;
  if (!response.ok) {
    throw new AuthError(
      "UNKNOWN",
      `GET /users/me failed with ${response.status}`,
      response.status,
    );
  }
  return (await response.json()) as UserRead;
}
