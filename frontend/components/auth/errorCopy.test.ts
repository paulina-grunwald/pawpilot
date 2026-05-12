import { describe, expect, it } from "vitest";
import {
  GENERIC_ERROR_COPY,
  NETWORK_ERROR_COPY,
  flashCopy,
  loginErrorCopy,
  resetPasswordErrorCopy,
  signupErrorCopy,
} from "./errorCopy";

describe("errorCopy", () => {
  it("login maps bad credentials to 'Incorrect email or password.'", () => {
    expect(loginErrorCopy.LOGIN_BAD_CREDENTIALS).toBe(
      "Incorrect email or password.",
    );
  });

  it("login does not leak whether the email exists (LOGIN_USER_NOT_VERIFIED uses same copy)", () => {
    expect(loginErrorCopy.LOGIN_USER_NOT_VERIFIED).toBe(
      loginErrorCopy.LOGIN_BAD_CREDENTIALS,
    );
  });

  it("login maps NETWORK_ERROR to network copy", () => {
    expect(loginErrorCopy.NETWORK_ERROR).toBe(NETWORK_ERROR_COPY);
  });

  it("signup maps existing-user to the friendly copy", () => {
    expect(signupErrorCopy.REGISTER_USER_ALREADY_EXISTS).toContain(
      "already exists",
    );
  });

  it("signup falls back to generic copy for unrelated codes", () => {
    expect(signupErrorCopy.LOGIN_BAD_CREDENTIALS).toBe(GENERIC_ERROR_COPY);
  });

  it("reset maps bad token to invalid/expired copy", () => {
    expect(resetPasswordErrorCopy.RESET_PASSWORD_BAD_TOKEN).toContain(
      "invalid or has expired",
    );
  });

  it("reset maps invalid password to dedicated copy", () => {
    expect(resetPasswordErrorCopy.RESET_PASSWORD_INVALID_PASSWORD).toContain(
      "doesn't meet",
    );
  });

  it("password-reset-success flash maps to the documented copy", () => {
    expect(flashCopy["password-reset-success"]).toBe(
      "Password updated — please log in.",
    );
  });
});
