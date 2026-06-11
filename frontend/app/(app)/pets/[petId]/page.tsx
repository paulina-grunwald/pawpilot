import { notFound } from "next/navigation";
import { PetDetailView } from "@/app/_components/pets/PetDetailView";
import { requireCurrentUser } from "@/lib/auth.server";
import { toDetailPet } from "@/lib/pets.format";
import { fetchPetById } from "@/lib/pets.server";

type PetDetailPageProps = {
  params: Promise<{ petId: string }>;
};

export default async function PetDetailPage({ params }: PetDetailPageProps) {
  await requireCurrentUser();
  const { petId } = await params;
  const pet = await fetchPetById(petId);
  if (!pet) {
    notFound();
  }
  return <PetDetailView pet={toDetailPet(pet)} />;
}
