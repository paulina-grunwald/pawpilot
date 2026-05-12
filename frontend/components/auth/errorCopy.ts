import type { AuthErrorCode } from "@/lib/auth";

export const GENERIC_ERROR_COPY = "Something went wrong, please try again.";
export const NETWORK_ERROR_COPY =
  "Couldn't reach the server. Check your connection and try again.";

export const loginErrorCopy: Record<AuthErrorCode, string> = {
  REGISTER_USER_ALREADY_EXISTS: GENERIC_ERROR_COPY,
  REGISTER_INVALID_PASSWORD: GENERIC_ERROR_COPY,
  LOGIN_BAD_CREDENTIALS: "Incorrect email or password.",
  LOGIN_USER_NOT_VERIFIED: "Incorrect email or password.",
  RESET_PASSWORD_BAD_TOKEN: GENERIC_ERROR_COPY,
  RESET_PASSWORD_INVALID_PASSWORD: GENERIC_ERROR_COPY,
  VALIDATION_ERROR: GENERIC_ERROR_COPY,
  NETWORK_ERROR: NETWORK_ERROR_COPY,
  UNKNOWN: GENERIC_ERROR_COPY,
};

export const signupErrorCopy: Record<AuthErrorCode, string> = {
  REGISTER_USER_ALREADY_EXISTS:
    "An account with that email already exists. Try logging in.",
  REGISTER_INVALID_PASSWORD: "That password doesn't meet the requirements.",
  LOGIN_BAD_CREDENTIALS: GENERIC_ERROR_COPY,
  LOGIN_USER_NOT_VERIFIED: GENERIC_ERROR_COPY,
  RESET_PASSWORD_BAD_TOKEN: GENERIC_ERROR_COPY,
  RESET_PASSWORD_INVALID_PASSWORD: GENERIC_ERROR_COPY,
  VALIDATION_ERROR: GENERIC_ERROR_COPY,
  NETWORK_ERROR: NETWORK_ERROR_COPY,
  UNKNOWN: GENERIC_ERROR_COPY,
};

export const resetPasswordErrorCopy: Record<AuthErrorCode, string> = {
  REGISTER_USER_ALREADY_EXISTS: GENERIC_ERROR_COPY,
  REGISTER_INVALID_PASSWORD: GENERIC_ERROR_COPY,
  LOGIN_BAD_CREDENTIALS: GENERIC_ERROR_COPY,
  LOGIN_USER_NOT_VERIFIED: GENERIC_ERROR_COPY,
  RESET_PASSWORD_BAD_TOKEN: "This reset link is invalid or has expired.",
  RESET_PASSWORD_INVALID_PASSWORD: "Your password doesn't meet the requirements.",
  VALIDATION_ERROR: GENERIC_ERROR_COPY,
  NETWORK_ERROR: NETWORK_ERROR_COPY,
  UNKNOWN: GENERIC_ERROR_COPY,
};

export const flashCopy: Record<string, string> = {
  "password-reset-success": "Password updated — please log in.",
};
