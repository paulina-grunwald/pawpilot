import { z } from "zod";

export const emailField = z
  .string({ error: "Email is required" })
  .min(1, "Email is required")
  .pipe(z.email({ error: "Enter a valid email address" }));

export const passwordField = z
  .string({ error: "Password is required" })
  .min(1, "Password is required")
  .min(8, "Password must be at least 8 characters");

export const loginSchema = z.object({
  email: emailField,
  password: z.string().min(1, "Password is required"),
});
export type LoginInput = z.infer<typeof loginSchema>;

export const signupSchema = z.object({
  email: emailField,
  password: passwordField,
});
export type SignupInput = z.infer<typeof signupSchema>;

export const forgotPasswordSchema = z.object({
  email: emailField,
});
export type ForgotPasswordInput = z.infer<typeof forgotPasswordSchema>;

export const resetPasswordSchema = z
  .object({
    token: z.string().min(1),
    password: passwordField,
    passwordConfirm: z.string().min(1, "Confirm your password"),
  })
  .refine((values) => values.password === values.passwordConfirm, {
    message: "Passwords don't match",
    path: ["passwordConfirm"],
  });
export type ResetPasswordInput = z.infer<typeof resetPasswordSchema>;
