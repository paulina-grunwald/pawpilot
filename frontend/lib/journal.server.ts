import "server-only";
import { cookies } from "next/headers";
import { AUTH_COOKIE_NAME } from "./auth.constants";
import { getApiBaseUrl } from "./auth";
import {
  buildJournalSearchParams,
  JournalError,
  parseJournalResponse,
  type JournalListParams,
} from "./journal";
import {
  journalEntryListResponseSchema,
  type JournalEntryListResponse,
} from "./journal.schemas";

async function getCookieHeader(): Promise<string | null> {
  const cookieStore = await cookies();
  const authCookie = cookieStore.get(AUTH_COOKIE_NAME);
  if (!authCookie) return null;
  return `${authCookie.name}=${authCookie.value}`;
}

export async function fetchJournalEntries(
  petId: string,
  params: JournalListParams = {},
): Promise<JournalEntryListResponse> {
  const cookieHeader = await getCookieHeader();
  if (!cookieHeader) {
    throw new JournalError("JOURNAL_UNAUTHENTICATED", "no auth cookie", 401);
  }
  const query = buildJournalSearchParams(params).toString();
  const suffix = query ? `?${query}` : "";
  const response = await fetch(`${getApiBaseUrl()}/pets/${petId}/journal${suffix}`, {
    headers: { cookie: cookieHeader },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new JournalError(
      response.status === 401 ? "JOURNAL_UNAUTHENTICATED" : "UNKNOWN",
      `GET /pets/${petId}/journal failed with ${response.status}`,
      response.status,
    );
  }
  return parseJournalResponse(journalEntryListResponseSchema, await response.json());
}
