import { requireCurrentUser } from "@/lib/auth.server";

export default async function DashboardPage() {
  const user = await requireCurrentUser();

  return (
    <main className="container-x py-12">
      <h1 className="display text-[28px] font-semibold text-ink">
        Welcome, {user.email}
      </h1>
      <p className="mt-3 text-[15px] text-muted">
        Your dashboard is coming soon.
      </p>
    </main>
  );
}
