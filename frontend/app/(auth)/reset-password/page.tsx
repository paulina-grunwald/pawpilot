"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthCard } from "@/components/auth/AuthCard";
import { Field } from "@/components/auth/Field";
import { SubmitButton } from "@/components/auth/SubmitButton";
import { resetPasswordErrorCopy } from "@/components/auth/errorCopy";
import { AuthError, resetPassword } from "@/lib/auth";
import {
  resetPasswordSchema,
  type ResetPasswordInput,
} from "@/lib/auth.schemas";

function ResetPasswordPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [formError, setFormError] = useState<string | null>(null);
  const [tokenInvalid, setTokenInvalid] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordInput>({
    resolver: zodResolver(resetPasswordSchema),
    mode: "onSubmit",
    defaultValues: { token: token ?? "", password: "", passwordConfirm: "" },
  });

  if (!token) {
    return (
      <AuthCard
        title="Reset link invalid"
        subtitle="This reset link is invalid or expired."
      >
        <Link
          href="/forgot-password"
          className="focus-ring inline-flex w-full items-center justify-center rounded-full px-4 py-2.5 text-[14px] font-medium text-paper no-underline"
          style={{ background: "var(--ink)" }}
        >
          Request a new link
        </Link>
      </AuthCard>
    );
  }

  const tokenValue: string = token;

  async function onSubmit(values: ResetPasswordInput) {
    setFormError(null);
    setTokenInvalid(false);
    try {
      await resetPassword({ ...values, token: tokenValue });
      router.replace("/login?flash=password-reset-success");
      router.refresh();
    } catch (caught) {
      if (caught instanceof AuthError) {
        if (caught.code === "RESET_PASSWORD_BAD_TOKEN") {
          setTokenInvalid(true);
          return;
        }
        if (caught.code === "RESET_PASSWORD_INVALID_PASSWORD") {
          setError("password", {
            type: "server",
            message: resetPasswordErrorCopy.RESET_PASSWORD_INVALID_PASSWORD,
          });
          return;
        }
        setFormError(resetPasswordErrorCopy[caught.code]);
        return;
      }
      throw caught;
    }
  }

  if (tokenInvalid) {
    return (
      <AuthCard
        title="Reset link expired"
        subtitle="This reset link is invalid or has expired."
      >
        <Link
          href="/forgot-password"
          className="focus-ring inline-flex w-full items-center justify-center rounded-full px-4 py-2.5 text-[14px] font-medium text-paper no-underline"
          style={{ background: "var(--ink)" }}
        >
          Request a new link
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Set a new password"
      subtitle="Pick something at least 8 characters long."
    >
      <form
        noValidate
        className="mt-4 flex flex-col gap-4"
        onSubmit={handleSubmit(onSubmit)}
      >
        <Field
          label="New password"
          type="password"
          autoComplete="new-password"
          error={errors.password?.message}
          {...register("password")}
        />
        <Field
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          error={errors.passwordConfirm?.message}
          {...register("passwordConfirm")}
        />
        {formError && (
          <p
            role="alert"
            className="rounded-lg border px-3 py-2 text-[13px]"
            style={{
              borderColor: "var(--terracotta)",
              background: "color-mix(in srgb, var(--terracotta) 8%, transparent)",
              color: "var(--terracotta-deep)",
            }}
          >
            {formError}
          </p>
        )}
        <SubmitButton isSubmitting={isSubmitting} loadingLabel="Updating password…">
          {isSubmitting ? "Updating password…" : "Update password"}
        </SubmitButton>
      </form>
    </AuthCard>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordPageContent />
    </Suspense>
  );
}
