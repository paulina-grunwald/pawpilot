import { formatWeekday } from "@/lib/date";
import { formatWeightKg, meanWeightGrams, type WeightSeriesPoint } from "@/lib/weight";
import { LineChart } from "../LineChart";
import styles from "./WeightTrend.module.css";

type WeightTrendProps = {
  series?: WeightSeriesPoint[];
  rangeLabel?: string;
};

export function WeightTrend({ series, rangeLabel }: WeightTrendProps) {
  const isLoading = series === undefined;
  const points = series ?? [];
  const latest = points.at(-1);
  const headlineValue = latest ? formatWeightKg(latest.weightGrams) : "—";

  return (
    <section aria-label="Weight trend" className={styles.card}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>Weight</h3>
          <p className={styles.subtitle}>Past {rangeLabel ?? "7d"} · kilograms</p>
        </div>
        <div className={styles.headline}>
          <span className={`${styles.value} display`}>{headlineValue}</span>
          <span className={styles.unit}>latest</span>
        </div>
      </div>

      {points.length >= 2 ? (
        <LineChart
          values={points.map((point) => point.weightGrams)}
          days={points.map((point) => formatWeekday(point.date))}
          dates={points.map((point) => point.label)}
          height={180}
          color="var(--forest)"
          yFormat={(grams) => formatWeightKg(grams)}
          mean={meanWeightGrams(points) ?? undefined}
          seriesLabel="weigh-ins"
          meanLabel="average"
          accessibleLabel={`Weight over the past ${rangeLabel ?? "7 days"}`}
        />
      ) : (
        <div className={styles.placeholder} role="note">
          {isLoading
            ? "Loading weight history…"
            : points.length === 1
              ? `One weigh-in logged (${headlineValue}). Log another to see the trend.`
              : "Log weight entries in the journal to see the trend here."}
        </div>
      )}
    </section>
  );
}
