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
