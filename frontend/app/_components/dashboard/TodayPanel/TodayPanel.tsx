import { Chip } from "../../pets/Chip";
import { ActivityRing } from "../ActivityRing";
import { LineChart } from "../LineChart";
import { SleepSplitBars, type SleepSplitBar } from "../SleepSplitBars";
import { StatTile, type StatTileTone } from "../StatTile";
import styles from "./TodayPanel.module.css";

export type TodayMetric = {
  label: string;
  value: string;
  unit?: string;
  delta?: string;
  tone?: StatTileTone;
};

export type VitalsStatus = {
  label: string;
  tone: "positive" | "caution" | "neutral";
};

export type TodayPanelData = {
  activityPercent: number;
  activityLabel: string;
  activitySublabel: string;
  metrics: TodayMetric[];
  activityWeekMinutes: number[];
  sleepWeekMinutes: number[];
  weekDates?: readonly (string | number)[];
  weekDays?: readonly string[];
  activityGoal?: number;
  activityWeekMean?: number;
  sleepWeekMean?: number;
  vitalsStatus?: VitalsStatus;
};

const VITAL_TONE_COLOR: Record<VitalsStatus["tone"], string> = {
  positive: "var(--status-positive)",
  caution: "var(--status-caution)",
  neutral: "var(--paper-on-dark-sub)",
};

type TodayPanelProps = {
  petName: string;
  todayLabel: string;
  data?: TodayPanelData;
  sleepSplitBars?: SleepSplitBar[];
  rangeLabel?: string;
};

const PLACEHOLDER_METRICS: TodayMetric[] = [
  { label: "Active", value: "—", unit: "min" },
  { label: "Sleep", value: "—" },
  { label: "Resting HR", value: "—", unit: "bpm" },
  { label: "Respiratory", value: "—", unit: "rpm" },
  { label: "Distance", value: "—", unit: "km" },
  { label: "Calm time", value: "—" },
];

export function TodayPanel({
  petName,
  todayLabel,
  data,
  sleepSplitBars,
  rangeLabel,
}: TodayPanelProps) {
  const isPlaceholder = data === undefined;
  const metrics = data?.metrics ?? PLACEHOLDER_METRICS;
  const activityPercent = data?.activityPercent ?? 0;
  const activityLabel = data?.activityLabel ?? "—";
  const activitySublabel = data?.activitySublabel ?? "awaiting Tractive";
  const headingText = isPlaceholder
    ? `Connect Tractive to see ${petName}'s day`
    : `${petName}’s on track`;

  return (
    <>
      <section aria-label="Today's stats" className={styles.hero}>
        <div className={styles.heroHeader}>
          <div>
            <p className={styles.heroEyebrow}>Today — {todayLabel}</p>
            <h2 className={`${styles.heroHeading} display`}>{headingText}</h2>
          </div>
          <Chip variant="dark">
            <span
              aria-hidden
              className={styles.chipDot}
              style={{
                background: isPlaceholder
                  ? "var(--paper-on-dark-sub)"
                  : VITAL_TONE_COLOR[data.vitalsStatus?.tone ?? "neutral"],
              }}
            />
            {isPlaceholder
              ? "Wearable not connected"
              : (data.vitalsStatus?.label ?? "Vitals status unknown")}
          </Chip>
        </div>

        <div className={styles.heroBody}>
          <ActivityRing
            percent={activityPercent}
            size={210}
            label={activityLabel}
            sublabel={activitySublabel}
          />
          <div className={styles.statGrid}>
            {metrics.map((metric) => (
              <StatTile
                key={metric.label}
                label={metric.label}
                value={metric.value}
                unit={metric.unit}
                delta={metric.delta}
                tone={metric.tone}
                surface="dark"
                placeholder={isPlaceholder}
              />
            ))}
          </div>
        </div>

        {isPlaceholder && (
          <p className={styles.placeholderHint}>
            Connect Tractive to see today&rsquo;s data.
          </p>
        )}
      </section>

      <section aria-label="Weekly trends" className={styles.trends}>
        <TrendCard
          title="Activity"
          subtitle={`Past ${rangeLabel ?? "7d"} · minutes`}
          value={isPlaceholder ? "—" : `${data.activityWeekMinutes.at(-1)}`}
          unit={isPlaceholder ? "min today" : "min today"}
        >
          {isPlaceholder ? (
            <ChartPlaceholder label="Activity trend will appear once Tractive is connected." />
          ) : (
            <LineChart
              values={data.activityWeekMinutes}
              height={160}
              color="var(--warm)"
              days={data.weekDays}
              dates={data.weekDates}
              yFormat={(value) => `${value} min`}
              accessibleLabel="Activity, past 7 days"
              mean={data.activityWeekMean}
              goal={data.activityGoal}
            />
          )}
        </TrendCard>
        <TrendCard
          title="Sleep"
          subtitle={`Past ${rangeLabel ?? "7d"} · minutes asleep`}
          value={isPlaceholder ? "—" : formatSleep(data.sleepWeekMinutes.at(-1)!)}
          unit="last night"
        >
          {isPlaceholder ? (
            <ChartPlaceholder label="Sleep trend will appear once Tractive is connected." />
          ) : (
            <LineChart
              values={data.sleepWeekMinutes}
              height={160}
              color="var(--blue-midnight)"
              days={data.weekDays}
              dates={data.weekDates}
              yFormat={(value) =>
                `${Math.floor(value / 60)}h${String(value % 60).padStart(2, "0")}`
              }
              accessibleLabel="Sleep, past 7 days"
              mean={data.sleepWeekMean}
            />
          )}
        </TrendCard>
      </section>

      {!isPlaceholder && sleepSplitBars && sleepSplitBars.length > 0 && (
        <section aria-label="Sleep split per day" className={styles.trendCard}>
          <div className={styles.trendHeader}>
            <div>
              <h3 className={styles.trendTitle}>Sleep split</h3>
              <p className={styles.trendSubtitle}>
                Past {rangeLabel ?? "7d"} · night vs day naps
              </p>
            </div>
          </div>
          <SleepSplitBars
            bars={sleepSplitBars}
            accessibleLabel={`Sleep split per day, past ${rangeLabel ?? "7 days"}`}
          />
        </section>
      )}
    </>
  );
}

function formatSleep(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;
  return `${hours}h ${String(remaining).padStart(2, "0")}m`;
}

type TrendCardProps = {
  title: string;
  subtitle: string;
  value: string;
  unit: string;
  children: React.ReactNode;
};

function TrendCard({ title, subtitle, value, unit, children }: TrendCardProps) {
  return (
    <div className={styles.trendCard}>
      <div className={styles.trendHeader}>
        <div>
          <h3 className={styles.trendTitle}>{title}</h3>
          <p className={styles.trendSubtitle}>{subtitle}</p>
        </div>
        <div className="text-right">
          <span className={`${styles.trendValue} display`}>{value}</span>
          <span className={styles.trendUnit}>{unit}</span>
        </div>
      </div>
      {children}
    </div>
  );
}

function ChartPlaceholder({ label }: { label: string }) {
  return (
    <div className={styles.chartPlaceholder} role="note">
      {label}
    </div>
  );
}
