import styles from "./StatTile.module.css";

export type StatTileTone = "positive" | "caution" | "neutral";

const TONE_COLOR: Record<StatTileTone, string> = {
  positive: "var(--status-positive)",
  caution: "var(--status-caution)",
  neutral: "var(--paper-on-dark-sub)",
};

type StatTileProps = {
  label: string;
  value: string;
  unit?: string;
  delta?: string;
  tone?: StatTileTone;
  surface?: "dark" | "light";
  placeholder?: boolean;
};

export function StatTile({
  label,
  value,
  unit,
  delta,
  tone = "neutral",
  surface = "dark",
  placeholder = false,
}: StatTileProps) {
  const displayValue = placeholder ? "—" : value;
  const displayDelta = placeholder ? "Awaiting data" : delta;
  const isDark = surface === "dark";

  return (
    <div className={isDark ? styles.tileDark : styles.tileLight}>
      <p className={isDark ? styles.labelDark : styles.labelLight}>{label}</p>
      <div className={styles.valueRow}>
        <span className={`${isDark ? styles.valueDark : styles.valueLight} display`}>
          {displayValue}
        </span>
        {unit && !placeholder && (
          <span className={isDark ? styles.unitDark : styles.unitLight}>{unit}</span>
        )}
      </div>
      {displayDelta && (
        <p
          className={styles.delta}
          style={{ color: placeholder ? "var(--paper-on-dark-sub)" : TONE_COLOR[tone] }}
        >
          {displayDelta}
        </p>
      )}
    </div>
  );
}
