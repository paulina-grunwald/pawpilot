import Link from "next/link";
import type { ReactNode } from "react";
import { PawMark } from "@/app/_components/PawMark";
import { LogoutButton } from "@/components/auth/LogoutButton";
import { requireCurrentUser } from "@/lib/auth.server";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const user = await requireCurrentUser();

  return (
    <div className="relative z-2 min-h-[100dvh]">
      <header
        className="sticky top-0 z-50 border-b backdrop-blur"
        style={{
          borderColor: "var(--hairline)",
          background: "color-mix(in srgb, var(--paper) 88%, transparent)",
        }}
      >
        <div className="container-x flex h-[64px] items-center justify-between">
          <Link
            href="/dashboard"
            aria-label="PawPilot — dashboard"
            className="flex items-center gap-[10px] no-underline text-ink"
          >
            <PawMark size={40} />
            <span className="display text-[18px] font-semibold tracking-[-0.01em]">
              PawPilot
            </span>
          </Link>
          <div className="flex items-center gap-3">
            <span
              data-testid="current-user-email"
              className="text-[13px] text-muted"
            >
              Logged in as <span className="font-medium text-ink">{user.email}</span>
            </span>
            <LogoutButton />
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}
