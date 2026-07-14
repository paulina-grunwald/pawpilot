import type { CSSProperties } from "react";
import type { JournalEntryRead } from "@/lib/journal.schemas";
import { computeJournalStats } from "@/lib/journal.stats";
import { EntryTypeIcon } from "../EntryTypeIcon";
import { Sparkline } from "../Sparkline";
import styles from "./JournalStats.module.css";

type JournalStatsProps = {
  entries: JournalEntryRead[];
};

export function JournalStats({ entries }: JournalStatsProps) {
  const stats = computeJournalStats(entries);

  return (
    <dl className={styles.grid} aria-label="Journal highlights">
      {stats.map((stat) => (
        <div
          key={stat.key}
          className={`${styles.card} ${stat.present ? "" : styles.muted}`}
          style={{ "--stat-accent": `var(${stat.accentVar})` } as CSSProperties}
        >
          <div className={styles.topRow}>
            <dt className={styles.label}>{stat.label}</dt>
            <span className={styles.art}>
              {stat.sparkline ? (
                <Sparkline values={stat.sparkline} />
              ) : (
                <EntryTypeIcon type={stat.iconType} size={18} />
              )}
            </span>
          </div>
          <dd className={styles.value}>
            <span className={`${styles.number} display`}>{stat.value}</span>
            {stat.unit && <span className={styles.unit}>{stat.unit}</span>}
          </dd>
          <p className={styles.sub}>{stat.sub}</p>
        </div>
      ))}
    </dl>
  );
}
