"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthError, logout } from "@/lib/auth";

export function LogoutButton() {
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  async function handleClick() {
    if (isLoggingOut) return;
    setIsLoggingOut(true);
    try {
      await logout();
    } catch (caught) {
      if (!(caught instanceof AuthError)) throw caught;
    }
    router.replace("/login");
    router.refresh();
  }

  return (
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
  );
}
