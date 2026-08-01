import type {
  RespiratoryNightDayComparison,
  VitalsTrendsData,
  VitalTrendSeries,
} from "@/lib/tractive.format";
import { LineChart } from "../LineChart";
import styles from "./VitalsTrendCards.module.css";

type VitalsTrendCardsProps = {
  petName: string;
  data?: VitalsTrendsData;
  rangeLabel?: string;
};

export function VitalsTrendCards({ petName, data, rangeLabel }: VitalsTrendCardsProps) {
  return (
    <section aria-label="Vitals trends" className={styles.grid}>
      <VitalTrendCard
        title="Resting heart rate"
        unit="bpm"
        petName={petName}
        series={data?.heartRate}
        rangeLabel={rangeLabel}
        color="var(--terracotta)"
      />
      <VitalTrendCard
        title="Resting respiratory rate"
        unit="/min"
        petName={petName}
        series={data?.respiratoryRate}
        rangeLabel={rangeLabel}
        color="var(--blue)"
        nightDay={data?.respiratoryNightDay}
      />
    </section>
  );
}

type VitalTrendCardProps = {
  title: string;
  unit: string;
  petName: string;
  series?: VitalTrendSeries;
  rangeLabel?: string;
  color: string;
  nightDay?: RespiratoryNightDayComparison;
};

function VitalTrendCard({
  title,
  unit,
  petName,
  series,
  rangeLabel,
  color,
  nightDay,
}: VitalTrendCardProps) {
  const hasChart = series !== undefined && series.values.length >= 2;
  const hasBand = hasChart && series.typicalRange !== undefined;
  const latestDate = series !== undefined ? series.dates.at(-1) : undefined;

  return (
    <article className={styles.card}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>{title}</h3>
          <p className={styles.subtitle}>
            Past {rangeLabel ?? "7d"} · daily mean of resting readings
          </p>
        </div>
        <div className={styles.headline}>
          <span className={`${styles.value} display`}>
            {series?.latest === null || series === undefined
              ? "—"
              : Math.round(series.latest)}
          </span>
          <span className={styles.unit}>{unit}</span>
          {series?.latest !== null && latestDate !== undefined && (
            <span className={styles.asOf}>as of {latestDate}</span>
          )}
        </div>
      </div>

      {hasChart ? (
        <LineChart
          values={series.values}
          days={series.days}
          dates={series.dates}
          height={170}
          color={color}
          unit={` ${unit}`}
          baseline={series.typicalRange}
          baselineLabel={`typical for ${petName}`}
          seriesLabel="daily mean"
          accessibleLabel={`${title} over the past ${rangeLabel ?? "7 days"}`}
        />
      ) : (
        <div className={styles.placeholder} role="note">
          {series === undefined
            ? "Vitals will appear once Tractive is connected."
            : "Not enough resting readings in this range to chart honestly."}
        </div>
      )}

      {nightDay && (
        <p className={styles.nightDay}>
          Night {nightDay.nightMean}
          {unit} vs day {nightDay.dayMean}
          {unit} · from {nightDay.nightRecordCount + nightDay.dayRecordCount} resting
          readings
        </p>
      )}

      {series !== undefined && series.suppressedDayCount > 0 && (
        <p className={styles.footnote} role="note">
          {series.suppressedDayCount}{" "}
          {series.suppressedDayCount === 1 ? "day" : "days"} with too few readings not
          plotted.
          {hasBand &&
            ` The shaded band is ${petName}'s own typical range, not a clinical one.`}
        </p>
      )}
      {series !== undefined && series.suppressedDayCount === 0 && hasBand && (
        <p className={styles.footnote} role="note">
          The shaded band is {petName}&rsquo;s own typical range, not a clinical one.
        </p>
      )}
    </article>
  );
}
