"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import type { PetPickerOption } from "@/app/_components/pets/PetPicker";
import { activePetStorageKey, petIdFromPathname } from "@/lib/activePet";

/**
 * Resolve which dog the chat is about without making the user pick one: the dog
 * named in the current route wins, then the dog they last focused (the same
 * value the dashboard and journal share), then the first pet. Reacts to route
 * changes so the floating widget follows the dashboard the user is looking at.
 */
export function useActivePetId(pets: PetPickerOption[], userId: string): string {
  const pathname = usePathname();
  const routePetId = petIdFromPathname(pathname);
  const [storedPetId, setStoredPetId] = useState<string | null>(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setStoredPetId(window.localStorage.getItem(activePetStorageKey(userId)));
  }, [userId, pathname]);

  const owned = (petId: string | null): string | null =>
    petId && pets.some((pet) => pet.id === petId) ? petId : null;

  return owned(routePetId) ?? owned(storedPetId) ?? pets[0].id;
}
