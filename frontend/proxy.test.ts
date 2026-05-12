import { describe, expect, it } from "vitest";
import { buildAuthRedirect } from "./proxy";

const baseUrl = "http://localhost:3000";

describe("buildAuthRedirect", () => {
  it("redirects unauthenticated visits to /dashboard → /login", () => {
    expect(
      buildAuthRedirect({
        pathname: "/dashboard",
        hasAuthCookie: false,
        baseUrl,
      }).redirectTo,
    ).toBe("http://localhost:3000/login");
  });

  it("redirects unauthenticated visits to nested protected paths", () => {
    expect(
      buildAuthRedirect({
        pathname: "/dashboard/settings",
        hasAuthCookie: false,
        baseUrl,
      }).redirectTo,
    ).toBe("http://localhost:3000/login");
  });

  it("allows authenticated visitors to access /dashboard", () => {
    expect(
      buildAuthRedirect({
        pathname: "/dashboard",
        hasAuthCookie: true,
        baseUrl,
      }).redirectTo,
    ).toBeNull();
  });

  it("redirects authenticated visits to /login → /dashboard", () => {
    expect(
      buildAuthRedirect({
        pathname: "/login",
        hasAuthCookie: true,
        baseUrl,
      }).redirectTo,
    ).toBe("http://localhost:3000/dashboard");
  });

  it("redirects authenticated visits to /signup → /dashboard", () => {
    expect(
      buildAuthRedirect({
        pathname: "/signup",
        hasAuthCookie: true,
        baseUrl,
      }).redirectTo,
    ).toBe("http://localhost:3000/dashboard");
  });

  it("redirects authenticated visits to /reset-password → /dashboard (regardless of ?token=)", () => {
    expect(
      buildAuthRedirect({
        pathname: "/reset-password",
        hasAuthCookie: true,
        baseUrl,
      }).redirectTo,
    ).toBe("http://localhost:3000/dashboard");
  });

  it("allows unauthenticated visits to auth pages", () => {
    expect(
      buildAuthRedirect({
        pathname: "/login",
        hasAuthCookie: false,
        baseUrl,
      }).redirectTo,
    ).toBeNull();
    expect(
      buildAuthRedirect({
        pathname: "/signup",
        hasAuthCookie: false,
        baseUrl,
      }).redirectTo,
    ).toBeNull();
    expect(
      buildAuthRedirect({
        pathname: "/forgot-password",
        hasAuthCookie: false,
        baseUrl,
      }).redirectTo,
    ).toBeNull();
    expect(
      buildAuthRedirect({
        pathname: "/reset-password",
        hasAuthCookie: false,
        baseUrl,
      }).redirectTo,
    ).toBeNull();
  });

  it("does not redirect when visiting unrelated paths (e.g. /)", () => {
    expect(
      buildAuthRedirect({
        pathname: "/",
        hasAuthCookie: false,
        baseUrl,
      }).redirectTo,
    ).toBeNull();
    expect(
      buildAuthRedirect({
        pathname: "/",
        hasAuthCookie: true,
        baseUrl,
      }).redirectTo,
    ).toBeNull();
  });
});
