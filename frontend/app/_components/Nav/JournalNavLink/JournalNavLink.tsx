"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { activePetStorageKey, petIdFromPathname } from "@/lib/activePet";

type JournalNavLinkProps = {
  userId: string;
  className?: string;
};

export function JournalNavLink({ userId, className }: JournalNavLinkProps) {
  const pathname = usePathname();
  const routePetId = petIdFromPathname(pathname);
  const [storedPetId, setStoredPetId] = useState<string | null>(null);

  // When the route doesn't name a pet (chat, add-pet, the /dashboard resolver)
  // fall back to the last dog the user focused.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setStoredPetId(window.localStorage.getItem(activePetStorageKey(userId)));
  }, [userId, pathname]);

  const petId = routePetId ?? storedPetId;
  const href = petId ? `/pets/${petId}/journal` : "/dashboard";

  return (
    <Link href={href} className={className}>
      Journal
    </Link>
  );
}
