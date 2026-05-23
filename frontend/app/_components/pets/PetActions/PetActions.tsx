"use client";

import Link from "next/link";
import { useState } from "react";
import { DeletePetDialog } from "../DeletePetDialog";
import { PetPickerButton } from "../PetPickerButton";

type PetActionsProps = {
  petId: string;
  petName: string;
};

export function PetActions({ petId, petName }: PetActionsProps) {
  const [deleteOpen, setDeleteOpen] = useState(false);

  return (
    <>
      <Link href={`/pets/${petId}/edit`} aria-label={`Edit ${petName}`}>
        <PetPickerButton variant="primary" tabIndex={-1}>
          Edit pet
        </PetPickerButton>
      </Link>
      <PetPickerButton disabled aria-disabled="true">
        Connect Tractive
      </PetPickerButton>
      <PetPickerButton variant="danger" onClick={() => setDeleteOpen(true)}>
        Delete
      </PetPickerButton>
      <DeletePetDialog
        open={deleteOpen}
        petId={petId}
        petName={petName}
        onClose={() => setDeleteOpen(false)}
      />
    </>
  );
}
