import type { SleepQualityData } from "@/lib/tractive.format";
import { LineChart } from "../LineChart";
import styles from "./SleepQualityCard.module.css";

type SleepQualityCardProps = {
  petName: string;
  data?: SleepQualityData;
  rangeLabel?: string;
};

function formatBoutHoursMinutes(totalMinutes: number): string {
  const minutes = Math.max(0, Math.round(totalMinutes));
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return `${hours}h ${String(remainder).padStart(2, "0")}m`;
}

export function SleepQualityCard({ petName, data, rangeLabel }: SleepQualityCardProps) {
  const hasChart = data !== undefined && data.values.length >= 2;

  return (
    <section aria-label="Sleep continuity" className={styles.card}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>Sleep continuity</h3>
          <p className={styles.subtitle}>
            Past {rangeLabel ?? "7d"} · longest unbroken rest stretch per day
          </p>
        </div>
        <div className={styles.headline}>
          <span className={`${styles.value} display`}>
            {data?.latestLongestBoutMinutes == null
              ? "—"
              : formatBoutHoursMinutes(data.latestLongestBoutMinutes)}
          </span>
          <span className={styles.unit}>latest</span>
        </div>
      </div>

      {hasChart ? (
        <LineChart
          values={data.values}
          days={data.days}
          dates={data.dates}
          height={170}
          color="var(--blue-deep)"
          yFormat={(value) => formatBoutHoursMinutes(value)}
          seriesLabel="longest rest stretch"
          accessibleLabel={`Longest unbroken rest stretch per day over the past ${rangeLabel ?? "7 days"}`}
        />
      ) : (
        <div className={styles.placeholder} role="note">
          {data === undefined
            ? "Sleep continuity will appear once Tractive is connected."
            : "Not enough days in this range to chart rest stretches."}
        </div>
      )}

      {data !== undefined && (
        <p className={styles.footnote} role="note">
          {petName} averages {data.averageBoutCount} rest stretches per day
          {data.averageFragmentationIndex !== null &&
            `, with ${data.averageFragmentationIndex} brief wake-ups per hour of rest`}
          . These describe how consolidated rest was, not deep or light sleep, which
          this tracker cannot see.
          {data.lowCoverageDayCount > 0 &&
            ` ${data.lowCoverageDayCount} ${
              data.lowCoverageDayCount === 1 ? "day" : "days"
            } with missing data understate rest.`}
        </p>
      )}
    </section>
  );
}
