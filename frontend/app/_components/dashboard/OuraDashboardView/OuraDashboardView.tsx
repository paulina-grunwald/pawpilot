import type { ReactNode } from "react";
import type { SleepSplitBar } from "../SleepSplitBars";
import { PetCard, type PetCardData } from "../../pets/PetCard";
import { TodayPanel, type TodayPanelData } from "../TodayPanel";
import styles from "./OuraDashboardView.module.css";

export type DashboardPet = PetCardData;

type OuraDashboardViewProps = {
  pet: DashboardPet;
  headerActions?: ReactNode;
  todayLabel: string;
  todayData?: TodayPanelData;
  sleepSplitBars?: SleepSplitBar[];
  rangeLabel?: string;
};

export function OuraDashboardView({
  pet,
  headerActions,
  todayLabel,
  todayData,
  sleepSplitBars,
  rangeLabel,
}: OuraDashboardViewProps) {
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
    </main>
  );
}
