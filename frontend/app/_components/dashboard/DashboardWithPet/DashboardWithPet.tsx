"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { PetRead } from "@/lib/pets";
import { toDashboardPet } from "@/lib/pets.format";
import { PetPicker } from "../../pets/PetPicker";
import { OuraDashboardView } from "../OuraDashboardView";
import styles from "./DashboardWithPet.module.css";

type DashboardWithPetProps = {
  pets: PetRead[];
  userId: string;
  todayLabel: string;
};

export function activePetStorageKey(userId: string): string {
  return `pawpilot:active-pet:${userId}`;
}

export function DashboardWithPet({ pets, userId, todayLabel }: DashboardWithPetProps) {
  const [storedPetId, setStoredPetId] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setStoredPetId(window.localStorage.getItem(activePetStorageKey(userId)));
    setHydrated(true);
  }, [userId]);

  function handleSelect(petId: string) {
    setStoredPetId(petId);
    window.localStorage.setItem(activePetStorageKey(userId), petId);
  }

  const activePet =
    (storedPetId && pets.find((pet) => pet.id === storedPetId)) || pets[0];
  const dashboardPet = toDashboardPet(activePet);
  const pickerOptions = pets.map((pet) => ({
    id: pet.id,
    name: pet.name,
    breed: pet.breed_other ?? "Mixed / unknown",
  }));

  const headerActions = (
    <>
      {pets.length > 1 && hydrated && (
        <PetPicker
          pets={pickerOptions}
          activePetId={activePet.id}
          onSelect={handleSelect}
        />
      )}
      {pets.length === 1 && (
        <Link href="/pets/new" className={styles.addLink}>
          + Add
        </Link>
      )}
    </>
  );

  if (!hydrated && pets.length > 1) {
    return (
      <div aria-busy="true" aria-live="polite" className={styles.hydrating} />
    );
  }

  return (
    <OuraDashboardView
      pet={dashboardPet}
      headerActions={headerActions}
      todayLabel={todayLabel}
    />
  );
}
