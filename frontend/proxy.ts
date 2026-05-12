import { NextResponse, type NextRequest } from "next/server";
import { AUTH_COOKIE_NAME } from "@/lib/auth.constants";

const PROTECTED_PATH_PREFIXES = ["/dashboard"];
const AUTH_PATH_PREFIXES = [
  "/login",
  "/signup",
  "/forgot-password",
  "/reset-password",
];

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

export function proxy(request: NextRequest) {
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
  matcher: [
    "/dashboard/:path*",
    "/login",
    "/signup",
    "/forgot-password",
    "/reset-password",
  ],
};
