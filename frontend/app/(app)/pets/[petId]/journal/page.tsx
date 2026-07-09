import { notFound } from "next/navigation";
import { JournalTimeline } from "@/app/_components/journal/JournalTimeline";
import { requireCurrentUser } from "@/lib/auth.server";
import { fetchJournalEntries } from "@/lib/journal.server";
import { fetchPetById } from "@/lib/pets.server";

type JournalPageProps = {
  params: Promise<{ petId: string }>;
};

export default async function JournalPage({ params }: JournalPageProps) {
  await requireCurrentUser();
  const { petId } = await params;
  const pet = await fetchPetById(petId);
  if (!pet) {
    notFound();
  }
  const initialPage = await fetchJournalEntries(petId, { limit: 50 });
  return <JournalTimeline petId={pet.id} petName={pet.name} initialPage={initialPage} />;
}
