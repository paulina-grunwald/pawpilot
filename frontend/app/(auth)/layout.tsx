import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="relative z-2 flex min-h-[100dvh] items-center justify-center px-6 py-12">
      {children}
    </main>
  );
}
