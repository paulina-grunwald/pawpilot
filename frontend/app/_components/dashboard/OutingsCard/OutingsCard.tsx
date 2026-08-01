import type { OutingsCardData } from "@/lib/tractive.format";
import styles from "./OutingsCard.module.css";

type OutingsCardProps = {
  petName: string;
  data?: OutingsCardData;
  rangeLabel?: string;
};

export function OutingsCard({ petName, data, rangeLabel }: OutingsCardProps) {
  return (
    <section aria-label="Walks and outings" className={styles.card}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>Walks &amp; outings</h3>
          <p className={styles.subtitle}>
            {data === undefined
              ? `Past ${rangeLabel ?? "7d"}`
              : `${data.latestDayLabel} · GPS-detected, counts are a floor`}
          </p>
        </div>
        <div className={styles.headline}>
          <span className={`${styles.value} display`}>
            {data === undefined ? "—" : `≥ ${data.latestCount}`}
          </span>
          <span className={styles.unit}>outings</span>
        </div>
      </div>

      {data === undefined ? (
        <div className={styles.placeholder} role="note">
          Walks will appear once Tractive is connected.
        </div>
      ) : data.latestRows.length === 0 ? (
        <div className={styles.placeholder} role="note">
          No outings detected on {data.latestDayLabel}. Gaps in GPS coverage can hide
          walks, so this is not proof {petName} stayed in.
        </div>
      ) : (
        <ul className={styles.list}>
          {data.latestRows.map((row, rowIndex) => (
            <li key={`${row.startLabel}-${rowIndex}`} className={styles.row}>
              <span className={`${styles.start} mono`}>{row.startLabel}</span>
              <span className={styles.duration}>{row.durationLabel}</span>
              <span className={styles.distance}>{row.distanceLabel}</span>
            </li>
          ))}
        </ul>
      )}

      {data !== undefined && data.rangeDailyAverage !== null && (
        <p className={styles.footnote} role="note">
          At least {data.rangeDailyAverage} outings per day on average across{" "}
          {data.daysInRange} days. Durations start and end at the first and last GPS fix
          away from home, so real walks run longer.
        </p>
      )}
    </section>
  );
}
