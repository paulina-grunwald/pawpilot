import { NextResponse, type NextRequest } from "next/server";
import { AUTH_COOKIE_NAME } from "@/lib/auth.constants";

// Auth gating runs in two independent layers:
//   1. This middleware does a cheap cookie-presence check for UX redirects
//      (kick anon users off /dashboard, kick authed users off /login).
//      Cookie presence is NOT a security boundary — a forged cookie passes.
//   2. The actual identity check happens in app/(app)/layout.tsx via
//      requireCurrentUser(), which validates the cookie against the backend.
// Do not collapse one layer into the other.

const PROTECTED_PATH_PREFIXES = ["/dashboard"];
const AUTH_PATH_PREFIXES = ["/login", "/signup"];

export function buildAuthRedirect(input: {
  pathname: string;
  hasAuthCookie: boolean;
  baseUrl: string;
}): { redirectTo: string | null } {
  const { pathname, hasAuthCookie, baseUrl } = input;
  const isProtected = PROTECTED_PATH_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
  const isAuthPath = AUTH_PATH_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );

  if (isProtected && !hasAuthCookie) {
    return { redirectTo: new URL("/login", baseUrl).toString() };
  }
  if (isAuthPath && hasAuthCookie) {
    return { redirectTo: new URL("/dashboard", baseUrl).toString() };
  }
  return { redirectTo: null };
}

export default function middleware(request: NextRequest) {
  const hasAuthCookie = request.cookies.has(AUTH_COOKIE_NAME);
  const { redirectTo } = buildAuthRedirect({
    pathname: request.nextUrl.pathname,
    hasAuthCookie,
    baseUrl: request.nextUrl.origin,
  });
  if (redirectTo) {
    return NextResponse.redirect(redirectTo);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/login", "/signup"],
};
