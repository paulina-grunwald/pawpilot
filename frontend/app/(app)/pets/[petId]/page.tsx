import { notFound } from "next/navigation";
import { JournalTeaserCard } from "@/app/_components/journal/JournalTeaserCard";
import { PetDetailView } from "@/app/_components/pets/PetDetailView";
import { requireCurrentUser } from "@/lib/auth.server";
import { fetchJournalEntries } from "@/lib/journal.server";
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
  const recentEntries = await fetchJournalEntries(petId, { limit: 3 });
  return (
    <PetDetailView
      pet={toDetailPet(pet)}
      journalCard={
        <JournalTeaserCard petId={pet.id} petName={pet.name} entries={recentEntries.items} />
      }
    />
  );
}
