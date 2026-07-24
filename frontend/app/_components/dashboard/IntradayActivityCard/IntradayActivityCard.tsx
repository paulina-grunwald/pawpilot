import type { IntradayActivityMatrix } from "@/lib/tractive.format";
import styles from "./IntradayActivityCard.module.css";

type IntradayActivityCardProps = {
  petName: string;
  matrix?: IntradayActivityMatrix;
  rangeLabel?: string;
};

const HOUR_AXIS_LABELS = [0, 6, 12, 18, 23];

// Any nonzero activity starts at this mix percentage so faint hours stay
// visibly warmer than truly quiet ones for low-vision and color-blind users;
// the top of the ramp shifts toward the deeper token to add a lightness step,
// not just a hue step.
const MINIMUM_ACTIVE_MIX_PERCENT = 20;

function cellFill(activeMinutes: number, maxActiveMinutes: number): string {
  if (maxActiveMinutes <= 0 || activeMinutes <= 0) {
    return "color-mix(in srgb, var(--surface-2) 70%, var(--card))";
  }
  const intensityFraction = Math.min(activeMinutes / maxActiveMinutes, 1);
  const intensityPercent = Math.round(
    MINIMUM_ACTIVE_MIX_PERCENT + intensityFraction * (100 - MINIMUM_ACTIVE_MIX_PERCENT),
  );
  const rampColor =
    intensityFraction > 0.6
      ? "color-mix(in srgb, var(--terracotta-deep) 45%, var(--warm))"
      : "var(--warm)";
  return `color-mix(in srgb, ${rampColor} ${intensityPercent}%, var(--surface-2))`;
}

function cellTitle(dayLabel: string, hour: number, activeMinutes: number): string {
  const hourLabel = `${String(hour).padStart(2, "0")}:00`;
  return `${dayLabel} ${hourLabel} · ${Math.round(activeMinutes)} min active`;
}

export function IntradayActivityCard({
  petName,
  matrix,
  rangeLabel,
}: IntradayActivityCardProps) {
  const rows = matrix?.rows ?? [];
  const maxActiveMinutes = matrix?.maxActiveMinutes ?? 0;
  const labelStride = rows.length > 14 ? Math.ceil(rows.length / 7) : 1;

  return (
    <section aria-label="Intraday activity" className={styles.card}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>When is {petName} active?</h3>
          <p className={styles.subtitle}>
            Past {rangeLabel ?? "7d"} · active minutes per hour
          </p>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className={styles.placeholder} role="note">
          Hour-by-hour activity will appear once Tractive is connected.
        </div>
      ) : (
        <>
          <div className={styles.scroll}>
            <div
              className={styles.grid}
              role="img"
              aria-label={`Active minutes per hour across ${rows.length} days for ${petName}`}
            >
              <div className={styles.hourAxis} aria-hidden>
                <span className={styles.dayLabel} />
                <div className={styles.hourAxisTrack}>
                  {HOUR_AXIS_LABELS.map((hour) => (
                    <span
                      key={`hour-${hour}`}
                      className={styles.hourLabel}
                      style={{ left: `${(hour / 24) * 100}%` }}
                    >
                      {String(hour).padStart(2, "0")}
                    </span>
                  ))}
                </div>
              </div>
              {rows.map((row, rowIndex) => {
                const showLabel =
                  rowIndex % labelStride === 0 || rowIndex === rows.length - 1;
                return (
                  <div key={row.date} className={styles.row}>
                    <span className={`${styles.dayLabel} mono`}>
                      {showLabel ? row.dayLabel : ""}
                      {showLabel && row.lowCoverage ? "*" : ""}
                    </span>
                    <div className={styles.cells}>
                      {row.hourlyActiveMinutes.map((activeMinutes, hour) => (
                        <span
                          key={`${row.date}-${hour}`}
                          className={styles.cell}
                          style={{
                            background: cellFill(activeMinutes, maxActiveMinutes),
                          }}
                          title={cellTitle(row.dayLabel, hour, activeMinutes)}
                        />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          <div className={`${styles.legend} mono`}>
            <span className={styles.legendScale}>
              <span
                className={styles.legendSwatch}
                style={{ background: cellFill(0, maxActiveMinutes) }}
                aria-hidden
              />
              <span
                className={styles.legendSwatch}
                style={{
                  background: cellFill(maxActiveMinutes / 2, maxActiveMinutes),
                }}
                aria-hidden
              />
              <span
                className={styles.legendSwatch}
                style={{ background: cellFill(maxActiveMinutes, maxActiveMinutes) }}
                aria-hidden
              />
              quiet to busy
            </span>
            {rows.some((row) => row.lowCoverage) && (
              <span>* day with over 2h of missing data, totals are a floor</span>
            )}
          </div>
        </>
      )}
    </section>
  );
}
