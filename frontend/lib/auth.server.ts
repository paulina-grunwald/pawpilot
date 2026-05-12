import "server-only";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AUTH_COOKIE_NAME } from "./auth.constants";
import { getApiBaseUrl, type UserRead } from "./auth";

export async function fetchCurrentUserFromBackend(input: {
  cookieHeader: string | null;
  fetchImpl?: typeof fetch;
  baseUrl?: string;
}): Promise<UserRead | null> {
  const { cookieHeader } = input;
  if (!cookieHeader) return null;
  const fetchToUse = input.fetchImpl ?? fetch;
  const baseUrl = input.baseUrl ?? getApiBaseUrl();
  const response = await fetchToUse(`${baseUrl}/users/me`, {
    headers: { cookie: cookieHeader },
    cache: "no-store",
  });
  if (response.status === 401) return null;
  if (!response.ok) {
    throw new Error(`GET /users/me failed with ${response.status}`);
  }
  return (await response.json()) as UserRead;
}

export async function requireCurrentUser(): Promise<UserRead> {
  const cookieStore = await cookies();
  const authCookie = cookieStore.get(AUTH_COOKIE_NAME);
  if (!authCookie) redirect("/login");
  const cookieHeader = `${authCookie.name}=${authCookie.value}`;
  const user = await fetchCurrentUserFromBackend({ cookieHeader });
  if (!user) redirect("/login");
  return user;
}
