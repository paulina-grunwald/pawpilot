import { DashboardWithPet } from "@/app/_components/dashboard/DashboardWithPet";
import { OnboardingChecklist } from "@/app/_components/dashboard/OnboardingChecklist";
import { requireCurrentUser } from "@/lib/auth.server";
import { fetchPetsForCurrentUser } from "@/lib/pets.server";

function formatTodayLabel(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export default async function DashboardPage() {
  const user = await requireCurrentUser();
  const pets = await fetchPetsForCurrentUser();

  if (pets.length === 0) {
    return <OnboardingChecklist userEmail={user.email} />;
  }

  return (
    <DashboardWithPet pets={pets} userId={user.id} todayLabel={formatTodayLabel()} />
  );
}
