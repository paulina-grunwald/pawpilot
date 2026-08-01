import type { ReactNode } from "react";
import type {
  IntradayActivityMatrix,
  OutingsCardData,
  SleepQualityData,
  VitalsTrendsData,
} from "@/lib/tractive.format";
import type { WeightSeriesPoint } from "@/lib/weight";
import type { SleepSplitBar } from "../SleepSplitBars";
import { PetCard, type PetCardData } from "../../pets/PetCard";
import { IntradayActivityCard } from "../IntradayActivityCard";
import { OutingsCard } from "../OutingsCard";
import { SleepQualityCard } from "../SleepQualityCard";
import { TodayPanel, type TodayPanelData } from "../TodayPanel";
import { VitalsTrendCards } from "../VitalsTrendCards";
import { WeightTrend } from "../WeightTrend";
import styles from "./PetDashboardView.module.css";

export type DashboardPet = PetCardData;

type PetDashboardViewProps = {
  pet: DashboardPet;
  headerActions?: ReactNode;
  todayLabel: string;
  todayData?: TodayPanelData;
  sleepSplitBars?: SleepSplitBar[];
  intradayMatrix?: IntradayActivityMatrix;
  vitalsTrends?: VitalsTrendsData;
  outingsData?: OutingsCardData;
  sleepQuality?: SleepQualityData;
  weightSeries?: WeightSeriesPoint[];
  rangeLabel?: string;
};

export function PetDashboardView({
  pet,
  headerActions,
  todayLabel,
  todayData,
  sleepSplitBars,
  intradayMatrix,
  vitalsTrends,
  outingsData,
  sleepQuality,
  weightSeries,
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

      <VitalsTrendCards petName={pet.name} data={vitalsTrends} rangeLabel={rangeLabel} />

      <SleepQualityCard petName={pet.name} data={sleepQuality} rangeLabel={rangeLabel} />

      <OutingsCard petName={pet.name} data={outingsData} rangeLabel={rangeLabel} />

      <IntradayActivityCard
        petName={pet.name}
        matrix={intradayMatrix}
        rangeLabel={rangeLabel}
      />

      <WeightTrend series={weightSeries} rangeLabel={rangeLabel} />
    </main>
  );
}
