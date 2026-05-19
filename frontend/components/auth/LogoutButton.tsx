"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthError, logout } from "@/lib/auth";

export function LogoutButton() {
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleClick() {
    if (isLoggingOut) return;
    setIsLoggingOut(true);
    setErrorMessage(null);
    try {
      await logout();
    } catch (caught) {
      if (!(caught instanceof AuthError)) throw caught;

      if (caught.status !== 401) {
        setErrorMessage("Could not log out — please try again.");
        setIsLoggingOut(false);
        return;
      }
    }
    router.replace("/login");
    router.refresh();
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={handleClick}
        disabled={isLoggingOut}
        aria-busy={isLoggingOut || undefined}
        className="focus-ring inline-flex items-center rounded-full border px-3 py-1.5 text-[13px] font-medium transition-opacity disabled:cursor-not-allowed disabled:opacity-60"
        style={{
          borderColor: "var(--hairline-strong)",
          color: "var(--ink)",
          background: "var(--paper)",
        }}
      >
        {isLoggingOut ? "Logging out…" : "Log out"}
      </button>
      {errorMessage && (
        <p role="alert" className="text-[12px]" style={{ color: "var(--terracotta)" }}>
          {errorMessage}
        </p>
      )}
    </div>
  );
}
