import Link from "next/link";
import type { ReactNode } from "react";
import { PawMark } from "@/app/_components/PawMark";

type AuthCardProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
};

export function AuthCard({ title, subtitle, children, footer }: AuthCardProps) {
  return (
    <div className="mx-auto flex w-full max-w-[420px] flex-col gap-6">
      <Link
        href="/"
        aria-label="PawPilot — home"
        className="text-ink flex items-center justify-center gap-[10px] no-underline"
      >
        <PawMark size={48} />
        <span className="display text-[22px] font-semibold tracking-[-0.01em]">PawPilot</span>
      </Link>
      <section
        className="rounded-2xl border p-8 shadow-sm"
        style={{
          background: "var(--card)",
          borderColor: "var(--hairline)",
        }}
      >
        <header className="mb-6 text-center">
          <h1 className="display text-ink text-[28px] font-semibold tracking-[-0.01em]">{title}</h1>
          {subtitle && <p className="text-muted mt-2 text-[14px]">{subtitle}</p>}
        </header>
        {children}
      </section>
      {footer && <footer className="text-muted text-center text-[14px]">{footer}</footer>}
    </div>
  );
}
