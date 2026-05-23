import { PetForm } from "@/app/_components/pets/PetForm";
import { requireCurrentUser } from "@/lib/auth.server";

export default async function NewPetPage() {
  await requireCurrentUser();
  return <PetForm mode="create" />;
}
