import { redirect } from "next/navigation";
import { DashboardWithPet } from "@/app/_components/dashboard/DashboardWithPet";
import { requireCurrentUser } from "@/lib/auth.server";
import { fetchPetsForCurrentUser } from "@/lib/pets.server";

function formatTodayLabel(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

type DashboardPetPageProps = {
  params: Promise<{ petId: string }>;
};

export default async function DashboardPetPage({ params }: DashboardPetPageProps) {
  const user = await requireCurrentUser();
  const { petId } = await params;
  const pets = await fetchPetsForCurrentUser();

  // Send unknown or stale ids back through the resolver, which picks a valid dog.
  if (!pets.some((pet) => pet.id === petId)) {
    redirect("/dashboard");
  }

  return (
    <DashboardWithPet
      pets={pets}
      activePetId={petId}
      userId={user.id}
      todayLabel={formatTodayLabel()}
    />
  );
}
