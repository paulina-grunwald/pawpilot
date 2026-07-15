import type { ReactNode } from "react";
import type { WeightSeriesPoint } from "@/lib/weight";
import type { SleepSplitBar } from "../SleepSplitBars";
import { PetCard, type PetCardData } from "../../pets/PetCard";
import { TodayPanel, type TodayPanelData } from "../TodayPanel";
import { WeightTrend } from "../WeightTrend";
import styles from "./PetDashboardView.module.css";

export type DashboardPet = PetCardData;

type PetDashboardViewProps = {
  pet: DashboardPet;
  headerActions?: ReactNode;
  todayLabel: string;
  todayData?: TodayPanelData;
  sleepSplitBars?: SleepSplitBar[];
  weightSeries?: WeightSeriesPoint[];
  rangeLabel?: string;
};

export function PetDashboardView({
  pet,
  headerActions,
  todayLabel,
  todayData,
  sleepSplitBars,
  weightSeries,
  rangeLabel,
}: PetDashboardViewProps) {
  return (
    <main className={styles.page}>
      <section aria-label="Pet header" className={styles.petHeader}>
        <PetCard pet={pet} />
        {headerActions && <div className="flex gap-2 items-center">{headerActions}</div>}
      </section>

      <TodayPanel
        petName={pet.name}
        todayLabel={todayLabel}
        data={todayData}
        sleepSplitBars={sleepSplitBars}
        rangeLabel={rangeLabel}
      />

      <WeightTrend series={weightSeries} rangeLabel={rangeLabel} />
    </main>
  );
}
