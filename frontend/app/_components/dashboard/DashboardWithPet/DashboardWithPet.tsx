"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { activePetStorageKey } from "@/lib/activePet";
import type { PetRead } from "@/lib/pets";
import { toDashboardPet } from "@/lib/pets.format";
import { fetchTractiveRollups, type TractiveDailySummary } from "@/lib/tractive";
import {
  toIntradayActivityMatrix,
  toOutingsCardData,
  toSleepQualityData,
  toSleepSplitBars,
  toTodayPanelData,
  toVitalsTrends,
  GOAL_BASELINE_DAYS,
} from "@/lib/tractive.format";
import { fetchPetWeightSeries, type WeightSeriesPoint } from "@/lib/weight";
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
  activePetId: string;
  userId: string;
  todayLabel: string;
};

export function DashboardWithPet({ pets, activePetId, userId, todayLabel }: DashboardWithPetProps) {
  const router = useRouter();
  const [rollups, setRollups] = useState<TractiveDailySummary[] | null>(null);
  const [weightSeries, setWeightSeries] = useState<WeightSeriesPoint[] | undefined>(undefined);
  const [rangeDays, setRangeDays] = useState<number>(DEFAULT_RANGE_DAYS);

  const activePet = pets.find((pet) => pet.id === activePetId) ?? pets[0];
  const dashboardPet = toDashboardPet(activePet);

  // Remember the focused dog so /dashboard, the journal FAB, and the navbar
  // journal link all land on the same pet.
  useEffect(() => {
    window.localStorage.setItem(activePetStorageKey(userId), activePet.id);
  }, [activePet.id, userId]);

  useEffect(() => {
    let cancelled = false;
    fetchTractiveRollups(activePet.id, Math.max(rangeDays, GOAL_BASELINE_DAYS))
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
  }, [activePet.id, rangeDays]);

  useEffect(() => {
    let cancelled = false;
    fetchPetWeightSeries(activePet.id, rangeDays)
      .then((series) => {
        if (!cancelled) setWeightSeries(series);
      })
      .catch(() => {
        if (!cancelled) setWeightSeries([]);
      });
    return () => {
      cancelled = true;
    };
  }, [activePet.id, rangeDays]);

  function handleSelect(petId: string) {
    if (petId === activePet.id) return;
    window.localStorage.setItem(activePetStorageKey(userId), petId);
    router.push(`/dashboard/${petId}`);
  }

  const plotted = rollups ? rollups.slice(-rangeDays) : null;
  const goalBaseline = rollups ? rollups.slice(-GOAL_BASELINE_DAYS) : undefined;
  const todayData = plotted ? toTodayPanelData(plotted, goalBaseline) : undefined;
  const sleepSplitBars = plotted ? toSleepSplitBars(plotted) : [];
  const intradayMatrix = plotted ? toIntradayActivityMatrix(plotted) : undefined;
  const vitalsTrends = plotted ? toVitalsTrends(plotted) : undefined;
  const outingsData = plotted ? toOutingsCardData(plotted) : undefined;
  const sleepQuality = plotted ? toSleepQualityData(plotted) : undefined;
  const pickerOptions = pets.map((pet) => ({
    id: pet.id,
    name: pet.name,
    breed: pet.breed_other ?? "Mixed / unknown",
  }));

  const headerActions = (
    <>
      <RangeToggle options={RANGE_OPTIONS} activeDays={rangeDays} onChange={setRangeDays} />
      {pets.length > 1 && (
        <PetPicker pets={pickerOptions} activePetId={activePet.id} onSelect={handleSelect} />
      )}
      {pets.length === 1 && (
        <Link href="/pets/new" className={styles.addLink}>
          + Add
        </Link>
      )}
    </>
  );

  return (
    <PetDashboardView
      pet={dashboardPet}
      headerActions={headerActions}
      todayLabel={todayLabel}
      todayData={todayData}
      sleepSplitBars={sleepSplitBars}
      intradayMatrix={intradayMatrix}
      vitalsTrends={vitalsTrends}
      outingsData={outingsData}
      sleepQuality={sleepQuality}
      weightSeries={weightSeries}
      rangeLabel={
        RANGE_OPTIONS.find((option) => option.days === rangeDays)?.label ?? `${rangeDays}d`
      }
    />
  );
}
