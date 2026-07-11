"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { PetRead } from "@/lib/pets";
import { toDashboardPet } from "@/lib/pets.format";
import { fetchTractiveRollups, type TractiveDailySummary } from "@/lib/tractive";
import { toSleepSplitBars, toTodayPanelData } from "@/lib/tractive.format";
import { PetPicker } from "../../pets/PetPicker";
import { PetDashboardView } from "../PetDashboardView";
import { RangeToggle, type RangeOption } from "../RangeToggle";
import styles from "./DashboardWithPet.module.css";

const RANGE_OPTIONS: readonly RangeOption[] = [
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
];
const DEFAULT_RANGE_DAYS = 7;

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
  const [rollups, setRollups] = useState<TractiveDailySummary[] | null>(null);
  const [rangeDays, setRangeDays] = useState<number>(DEFAULT_RANGE_DAYS);

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

  useEffect(() => {
    if (!hydrated) return;
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRollups(null);
    fetchTractiveRollups(activePet.id, rangeDays)
      .then((response) => {
        if (!cancelled) setRollups(response.daily);
      })
      .catch(() => {
        // Fall back to the placeholder state on any error — the upload card on
        // the pet detail page is the surface for fixing this.
        if (!cancelled) setRollups([]);
      });
    return () => {
      cancelled = true;
    };
  }, [activePet.id, hydrated, rangeDays]);

  const todayData = rollups ? toTodayPanelData(rollups) : undefined;
  const sleepSplitBars = rollups ? toSleepSplitBars(rollups) : [];
  const pickerOptions = pets.map((pet) => ({
    id: pet.id,
    name: pet.name,
    breed: pet.breed_other ?? "Mixed / unknown",
  }));

  const headerActions = (
    <>
      <RangeToggle
        options={RANGE_OPTIONS}
        activeDays={rangeDays}
        onChange={setRangeDays}
      />
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
    <PetDashboardView
      pet={dashboardPet}
      headerActions={headerActions}
      todayLabel={todayLabel}
      todayData={todayData}
      sleepSplitBars={sleepSplitBars}
      rangeLabel={RANGE_OPTIONS.find((option) => option.days === rangeDays)?.label ?? `${rangeDays}d`}
    />
  );
}
