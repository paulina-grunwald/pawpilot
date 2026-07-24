"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { Sparkline } from "@/app/_components/dashboard/Sparkline";
import type { JournalEntryRead } from "@/lib/journal.schemas";
import { computeJournalStats } from "@/lib/journal.stats";
import { EntryTypeIcon } from "../EntryTypeIcon";
import styles from "./JournalStats.module.css";

type JournalStatsProps = {
  entries: JournalEntryRead[];
};

export function JournalStats({ entries }: JournalStatsProps) {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setNow(new Date());
  }, []);
  const stats = computeJournalStats(entries, now);

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
                <Sparkline
                  values={stat.sparkline}
                  width={62}
                  height={22}
                  color={`var(${stat.accentVar})`}
                  fill={false}
                  accessibleLabel={`${stat.label} trend, latest ${stat.value}${stat.unit ? ` ${stat.unit}` : ""}`}
                />
              ) : (
                <EntryTypeIcon type={stat.iconType} size={18} />
              )}
            </span>
          </div>
          <dd className={styles.value}>
            <span className={`${styles.number} display`}>{stat.value}</span>
            {stat.unit && <span className={styles.unit}>{stat.unit}</span>}
          </dd>
          <p className={styles.subtitle}>{stat.subtitle}</p>
        </div>
      ))}
    </dl>
  );
}
