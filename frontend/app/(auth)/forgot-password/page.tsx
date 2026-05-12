"use client";

import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthCard } from "@/components/auth/AuthCard";
import { Field } from "@/components/auth/Field";
import { SubmitButton } from "@/components/auth/SubmitButton";
import { AuthError, forgotPassword } from "@/lib/auth";
import {
  forgotPasswordSchema,
  type ForgotPasswordInput,
} from "@/lib/auth.schemas";

export default function ForgotPasswordPage() {
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    getValues,
  } = useForm<ForgotPasswordInput>({
    resolver: zodResolver(forgotPasswordSchema),
    mode: "onSubmit",
    defaultValues: { email: "" },
  });

  async function onSubmit(values: ForgotPasswordInput) {
    try {
      await forgotPassword(values);
    } catch (caught) {
      if (!(caught instanceof AuthError)) throw caught;
    }
    setSubmittedEmail(values.email);
  }

  async function handleResend() {
    const email = submittedEmail ?? getValues("email");
    if (!email) return;
    try {
      await forgotPassword({ email });
    } catch (caught) {
      if (!(caught instanceof AuthError)) throw caught;
    }
  }

  if (submittedEmail) {
    return (
      <AuthCard
        title="Check your email"
        subtitle={`If an account exists for ${submittedEmail}, we've sent a reset link. Check your inbox.`}
        footer={
          <span>
            <Link
              href="/login"
              className="font-medium underline"
              style={{ color: "var(--ink)" }}
            >
              Back to login
            </Link>
          </span>
        }
      >
        <button
          type="button"
          onClick={handleResend}
          className="focus-ring w-full rounded-full border px-4 py-2.5 text-[14px] font-medium"
          style={{
            borderColor: "var(--hairline-strong)",
            background: "var(--paper)",
            color: "var(--ink)",
          }}
        >
          Resend
        </button>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Forgot your password?"
      subtitle="Enter your email and we'll send you a reset link."
      footer={
        <span>
          Remembered it?{" "}
          <Link href="/login" className="font-medium underline" style={{ color: "var(--ink)" }}>
            Back to login
          </Link>
        </span>
      }
    >
      <form
        noValidate
        className="mt-4 flex flex-col gap-4"
        onSubmit={handleSubmit(onSubmit)}
      >
        <Field
          label="Email"
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />
        <SubmitButton isSubmitting={isSubmitting} loadingLabel="Sending link…">
          {isSubmitting ? "Sending link…" : "Send reset link"}
        </SubmitButton>
      </form>
    </AuthCard>
  );
}
