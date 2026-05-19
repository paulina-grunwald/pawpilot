import { NextResponse, type NextRequest } from "next/server";
import { AUTH_COOKIE_NAME } from "@/lib/auth.constants";


const PROTECTED_PATH_PREFIXES = ["/dashboard"];
const AUTH_PATH_PREFIXES = ["/login", "/signup"];
export const SESSION_EXPIRED_QUERY_KEY = "session";
export const SESSION_EXPIRED_QUERY_VALUE = "expired";

export function buildAuthRedirect(input: {
  pathname: string;
  hasAuthCookie: boolean;
  baseUrl: string;
  sessionExpired?: boolean;
}): { redirectTo: string | null } {
  const { pathname, hasAuthCookie, baseUrl, sessionExpired = false } = input;
  const isProtected = PROTECTED_PATH_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
  const isAuthPath = AUTH_PATH_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );

  if (isProtected && !hasAuthCookie) {
    return { redirectTo: new URL("/login", baseUrl).toString() };
  }
  if (isAuthPath && hasAuthCookie && !sessionExpired) {
    return { redirectTo: new URL("/dashboard", baseUrl).toString() };
  }
  return { redirectTo: null };
}

export default function proxy(request: NextRequest) {
  const hasAuthCookie = request.cookies.has(AUTH_COOKIE_NAME);
  const sessionExpired =
    request.nextUrl.searchParams.get(SESSION_EXPIRED_QUERY_KEY) ===
    SESSION_EXPIRED_QUERY_VALUE;
  const { redirectTo } = buildAuthRedirect({
    pathname: request.nextUrl.pathname,
    hasAuthCookie,
    baseUrl: request.nextUrl.origin,
    sessionExpired,
  });
  if (redirectTo) {
    return NextResponse.redirect(redirectTo);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/login", "/signup"],
};
