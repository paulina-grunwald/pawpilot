import { notFound } from "next/navigation";
import { PetForm } from "@/app/_components/pets/PetForm";
import { requireCurrentUser } from "@/lib/auth.server";
import { petReadToFormInput } from "@/lib/pets.schemas";
import { fetchPetById } from "@/lib/pets.server";

type EditPetPageProps = {
  params: Promise<{ petId: string }>;
};

export default async function EditPetPage({ params }: EditPetPageProps) {
  await requireCurrentUser();
  const { petId } = await params;
  const pet = await fetchPetById(petId);
  if (!pet) {
    notFound();
  }
  return (
    <PetForm
      mode="edit"
      petId={petId}
      initialValues={petReadToFormInput(pet)}
      existingPhotoUrl={pet.photo_url}
    />
  );
}
