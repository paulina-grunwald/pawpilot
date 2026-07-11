import { DashboardRedirect } from "@/app/_components/dashboard/DashboardRedirect";
import { OnboardingChecklist } from "@/app/_components/dashboard/OnboardingChecklist";
import { requireCurrentUser } from "@/lib/auth.server";
import { fetchPetsForCurrentUser } from "@/lib/pets.server";

export default async function DashboardPage() {
  const user = await requireCurrentUser();
  const pets = await fetchPetsForCurrentUser();

  if (pets.length === 0) {
    return <OnboardingChecklist userEmail={user.email} />;
  }

  return <DashboardRedirect userId={user.id} petIds={pets.map((pet) => pet.id)} />;
}
