import Link from "next/link";

export default function PetNotFound() {
  return (
    <main className="container-x" style={{ padding: "48px 0", textAlign: "center" }}>
      <h1 className="display" style={{ fontSize: 32, margin: 0 }}>
        We couldn&rsquo;t find that pet
      </h1>
      <p style={{ marginTop: 12, color: "var(--muted)" }}>
        The pet may have been deleted, or the link may be incorrect.
      </p>
      <p style={{ marginTop: 24 }}>
        <Link href="/dashboard">← Back to dashboard</Link>
      </p>
    </main>
  );
}
