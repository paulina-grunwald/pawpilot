"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { activePetStorageKey } from "@/lib/activePet";
import styles from "./DashboardRedirect.module.css";

type DashboardRedirectProps = {
  userId: string;
  petIds: string[];
};

/**
 * `/dashboard` has no pet in the URL, so this resolver sends the user on to the
 * pet-scoped dashboard, preferring the dog they last focused (persisted in
 * localStorage) and falling back to the first pet.
 */
export function DashboardRedirect({ userId, petIds }: DashboardRedirectProps) {
  const router = useRouter();

  useEffect(() => {
    const stored = window.localStorage.getItem(activePetStorageKey(userId));
    const target = stored && petIds.includes(stored) ? stored : petIds[0];
    router.replace(`/dashboard/${target}`);
  }, [router, userId, petIds]);

  return <div className={styles.pending} aria-busy="true" aria-live="polite" />;
}
