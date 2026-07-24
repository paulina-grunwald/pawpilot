import type { ReactNode } from "react";
import type { SleepSplitBar } from "../SleepSplitBars";
import { PetCard, type PetCardData } from "../../pets/PetCard";
import { TodayPanel, type TodayPanelData } from "../TodayPanel";
import styles from "./PetDashboardView.module.css";

export type DashboardPet = PetCardData;

type PetDashboardViewProps = {
  pet: DashboardPet;
  headerActions?: ReactNode;
  todayLabel: string;
  todayData?: TodayPanelData;
  sleepSplitBars?: SleepSplitBar[];
  rangeLabel?: string;
};

export function PetDashboardView({
  pet,
  headerActions,
  todayLabel,
  todayData,
  sleepSplitBars,
  rangeLabel,
}: PetDashboardViewProps) {
  return (
    <main className={styles.page}>
      <section aria-label="Pet header" className={styles.petHeader}>
        <PetCard pet={pet} />
        {headerActions && <div className="flex items-center gap-2">{headerActions}</div>}
      </section>

      <TodayPanel
        petName={pet.name}
        todayLabel={todayLabel}
        data={todayData}
        sleepSplitBars={sleepSplitBars}
        rangeLabel={rangeLabel}
      />
    </main>
  );
}
