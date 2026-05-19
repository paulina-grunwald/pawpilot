import { describe, it, expect } from "vitest";
import { loginSchema, signupSchema } from "./auth.schemas";

function firstError(
  result: { success: true } | { success: false; error: { issues: { path: PropertyKey[]; message: string }[] } },
  path: string,
): string | undefined {
  if (result.success) return undefined;
  return result.error.issues.find((issue) => issue.path.join(".") === path)?.message;
}

describe("loginSchema", () => {
  it("rejects empty email with 'Email is required'", () => {
    const result = loginSchema.safeParse({ email: "", password: "anything" });
    expect(firstError(result, "email")).toBe("Email is required");
  });

  it("rejects malformed email with 'Enter a valid email address'", () => {
    const result = loginSchema.safeParse({ email: "not-an-email", password: "pw" });
    expect(firstError(result, "email")).toBe("Enter a valid email address");
  });

  it("rejects empty password with 'Password is required'", () => {
    const result = loginSchema.safeParse({ email: "a@b.co", password: "" });
    expect(firstError(result, "password")).toBe("Password is required");
  });

  it("accepts a short password (login doesn't enforce min 8)", () => {
    const result = loginSchema.safeParse({ email: "a@b.co", password: "x" });
    expect(result.success).toBe(true);
  });

  it("accepts valid input", () => {
    const result = loginSchema.safeParse({ email: "a@b.co", password: "password" });
    expect(result.success).toBe(true);
  });
});

describe("signupSchema", () => {
  it("rejects password shorter than 8 chars", () => {
    const result = signupSchema.safeParse({ email: "a@b.co", password: "short" });
    expect(firstError(result, "password")).toBe(
      "Password must be at least 8 characters",
    );
  });

  it("rejects empty password with 'Password is required'", () => {
    const result = signupSchema.safeParse({ email: "a@b.co", password: "" });
    expect(firstError(result, "password")).toBe("Password is required");
  });

  it("accepts valid email + 8-char password", () => {
    const result = signupSchema.safeParse({
      email: "a@b.co",
      password: "12345678",
    });
    expect(result.success).toBe(true);
  });
});
