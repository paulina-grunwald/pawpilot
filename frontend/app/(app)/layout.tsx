import Link from "next/link";
import type { ReactNode } from "react";
import { ChatWidget } from "@/app/_components/chat/ChatWidget";
import { FloatingDockProvider } from "@/app/_components/floating/FloatingDockContext";
import { JournalFab } from "@/app/_components/floating/JournalFab";
import { PawMark } from "@/app/_components/PawMark";
import { LogoutButton } from "@/components/auth/LogoutButton";
import { requireCurrentUser } from "@/lib/auth.server";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const user = await requireCurrentUser();

  return (
    <FloatingDockProvider>
      <div className="relative z-2 min-h-dvh">
        <header
          className="sticky top-0 z-50 border-b backdrop-blur"
          style={{
            borderColor: "var(--hairline)",
            background: "color-mix(in srgb, var(--paper) 88%, transparent)",
          }}
        >
          <div className="container-x flex h-16 items-center justify-between">
            <Link
              href="/dashboard"
              aria-label="PawPilot — dashboard"
              className="text-ink flex items-center gap-2.5 no-underline"
            >
              <PawMark size={40} />
              <span className="display text-[18px] font-semibold tracking-[-0.01em]">PawPilot</span>
            </Link>
            <div className="flex items-center gap-4">
              <Link
                href="/chat"
                className="text-ink hover:text-blue text-[13px] font-medium no-underline"
              >
                Ask PawPilot
              </Link>
              <span data-testid="current-user-email" className="text-muted text-[13px]">
                Logged in as <span className="text-ink font-medium">{user.email}</span>
              </span>
              <LogoutButton />
            </div>
          </div>
        </header>
        {children}
        <ChatWidget />
        <JournalFab userId={user.id} />
      </div>
    </FloatingDockProvider>
  );
}
