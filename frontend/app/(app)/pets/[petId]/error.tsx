"use client";

import Link from "next/link";
import { useEffect } from "react";

type PetErrorBoundaryProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function PetErrorBoundary({ error, reset }: PetErrorBoundaryProps) {
  useEffect(() => {
    console.error("Pet detail route error:", error);
  }, [error]);

  return (
    <main className="container-x" style={{ padding: "48px 0", textAlign: "center" }}>
      <h1 className="display" style={{ fontSize: 32, margin: 0 }}>
        Something went wrong
      </h1>
      <p style={{ marginTop: 12, color: "var(--muted)" }}>
        We couldn&rsquo;t load this pet right now. Please try again.
      </p>
      <div style={{ marginTop: 24, display: "flex", gap: 12, justifyContent: "center" }}>
        <button
          type="button"
          onClick={reset}
          style={{
            padding: "8px 14px",
            borderRadius: 8,
            background: "var(--ink)",
            color: "var(--paper)",
            border: "none",
            cursor: "pointer",
            fontFamily: "inherit",
            fontSize: 13,
          }}
        >
          Try again
        </button>
        <Link href="/dashboard">Back to dashboard</Link>
      </div>
    </main>
  );
}
