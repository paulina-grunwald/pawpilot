"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthCard } from "@/components/auth/AuthCard";
import { Field } from "@/components/auth/Field";
import { SubmitButton } from "@/components/auth/SubmitButton";
import { signupErrorCopy } from "@/components/auth/errorCopy";
import { AuthError, login, signup } from "@/lib/auth";
import { signupSchema, type SignupInput } from "@/lib/auth.schemas";
import { useIsHydrated } from "@/lib/useIsHydrated";

export default function SignupPage() {
  const router = useRouter();
  const isHydrated = useIsHydrated();
  const [formError, setFormError] = useState<string | null>(null);
  const [accountExists, setAccountExists] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupInput>({
    resolver: zodResolver(signupSchema),
    mode: "onSubmit",
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: SignupInput) {
    setFormError(null);
    setAccountExists(false);
    try {
      await signup(values);
      await login(values);
      router.replace("/dashboard");
      router.refresh();
    } catch (caught) {
      if (caught instanceof AuthError) {
        if (caught.code === "REGISTER_USER_ALREADY_EXISTS") {
          setAccountExists(true);
        }
        setFormError(signupErrorCopy[caught.code]);
        return;
      }
      throw caught;
    }
  }

  return (
    <AuthCard
      title="Create your account"
      subtitle="Sign up to track your pup with PawPilot"
      footer={
        <span>
          Already have an account?{" "}
          <Link href="/login" className="font-medium underline" style={{ color: "var(--ink)" }}>
            Log in
          </Link>
        </span>
      }
    >
      <form
        noValidate
        method="post"
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
        <Field
          label="Password"
          type="password"
          autoComplete="new-password"
          helpText="At least 8 characters"
          error={errors.password?.message}
          {...register("password")}
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
            {accountExists && (
              <>
                {" "}
                <Link
                  href="/login"
                  className="font-medium underline"
                  style={{ color: "var(--terracotta-deep)" }}
                >
                  Log in instead
                </Link>
                .
              </>
            )}
          </p>
        )}
        <SubmitButton
          isSubmitting={isSubmitting}
          isHydrating={!isHydrated}
          loadingLabel="Creating account…"
        >
          {isSubmitting ? "Creating account…" : "Create account"}
        </SubmitButton>
      </form>
    </AuthCard>
  );
}
