"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthCard } from "@/components/auth/AuthCard";
import { Field } from "@/components/auth/Field";
import { SubmitButton } from "@/components/auth/SubmitButton";
import { FlashMessage } from "@/components/auth/FlashMessage";
import { loginErrorCopy } from "@/components/auth/errorCopy";
import { AuthError, login } from "@/lib/auth";
import { loginSchema, type LoginInput } from "@/lib/auth.schemas";

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const flash = searchParams.get("flash");
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    mode: "onSubmit",
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: LoginInput) {
    setFormError(null);
    try {
      await login(values);
      router.replace("/dashboard");
      router.refresh();
    } catch (caught) {
      if (caught instanceof AuthError) {
        setFormError(loginErrorCopy[caught.code]);
        return;
      }
      throw caught;
    }
  }

  return (
    <AuthCard
      title="Welcome back"
      subtitle="Log in to your PawPilot account"
      footer={
        <span>
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="font-medium underline" style={{ color: "var(--ink)" }}>
            Create account
          </Link>
        </span>
      }
    >
      <FlashMessage flashKey={flash} />
      <form
        noValidate
        className="mt-4 flex flex-col gap-4"
        onSubmit={handleSubmit(onSubmit)}
      >
        <Field
          label="Email"
          type="email"
          autoComplete="username"
          error={errors.email?.message}
          {...register("email")}
        />
        <Field
          label="Password"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register("password")}
        />
        <div className="-mt-2 text-right text-[13px]">
          <Link
            href="/forgot-password"
            className="underline"
            style={{ color: "var(--muted)" }}
          >
            Forgot password?
          </Link>
        </div>
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
        <SubmitButton isSubmitting={isSubmitting} loadingLabel="Logging in…">
          {isSubmitting ? "Logging in…" : "Log in"}
        </SubmitButton>
      </form>
    </AuthCard>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginPageContent />
    </Suspense>
  );
}
