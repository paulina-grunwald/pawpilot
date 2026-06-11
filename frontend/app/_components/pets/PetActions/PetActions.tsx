"use client";

import Link from "next/link";
import { useState } from "react";
import { DeletePetDialog } from "../DeletePetDialog";
import { PetActionButton } from "../PetActionButton";

type PetActionsProps = {
  petId: string;
  petName: string;
};

export function PetActions({ petId, petName }: PetActionsProps) {
  const [deleteOpen, setDeleteOpen] = useState(false);

  return (
    <>
      <Link href={`/pets/${petId}/edit`} aria-label={`Edit ${petName}`}>
        <PetActionButton variant="primary" tabIndex={-1}>
          Edit pet
        </PetActionButton>
      </Link>
      <PetActionButton variant="danger" onClick={() => setDeleteOpen(true)}>
        Delete
      </PetActionButton>
      <DeletePetDialog
        open={deleteOpen}
        petId={petId}
        petName={petName}
        onClose={() => setDeleteOpen(false)}
      />
    </>
  );
}
