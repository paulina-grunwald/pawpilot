"use client";

import { useId, useLayoutEffect, useRef, useState } from "react";
import styles from "./SleepSplitBars.module.css";

export type SleepSplitBar = {
  date: string;
  dayLabel: string;
  nightMinutes: number;
  dayMinutes: number;
};

type SleepSplitBarsProps = {
  bars: SleepSplitBar[];
  height?: number;
  accessibleLabel?: string;
};

function useMeasuredWidth() {
  const ref = useRef<HTMLDivElement | null>(null);
  const [measuredWidth, setMeasuredWidth] = useState(0);
  useLayoutEffect(() => {
    if (!ref.current) return;
    const node = ref.current;
    const observer = new ResizeObserver(([entry]) => setMeasuredWidth(entry.contentRect.width));
    observer.observe(node);
    setMeasuredWidth(node.getBoundingClientRect().width);
    return () => observer.disconnect();
  }, []);
  return [ref, measuredWidth] as const;
}

function formatHoursMinutes(totalMinutes: number): string {
  const minutes = Math.max(0, Math.round(totalMinutes));
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return `${hours}h ${String(remainder).padStart(2, "0")}m`;
}

export function SleepSplitBars({ bars, height = 200, accessibleLabel }: SleepSplitBarsProps) {
  const [containerRef, fullWidth] = useMeasuredWidth();
  const reactId = useId().replace(/[^a-z0-9]/gi, "");

  if (bars.length === 0) {
    return (
      <p className={styles.empty} role="note">
        No sleep data yet for this range.
      </p>
    );
  }

  const chartWidth = Math.max(fullWidth, 240);
  const paddingLeft = 44;
  const paddingRight = 12;
  const paddingTop = 12;
  const paddingBottom = 28;
  const innerWidth = chartWidth - paddingLeft - paddingRight;
  const innerHeight = height - paddingTop - paddingBottom;

  const totals = bars.map((bar) => bar.nightMinutes + bar.dayMinutes);
  const yMax = Math.max(60, ...totals) * 1.1;
  const yAt = (value: number) => paddingTop + (1 - value / yMax) * innerHeight;

  const trackGap = bars.length > 14 ? 2 : 6;
  const slotWidth = innerWidth / bars.length;
  const barWidth = Math.max(4, slotWidth - trackGap);
  // Smaller-text label spacing when many bars; only every Nth label.
  const labelStride = bars.length > 14 ? Math.ceil(bars.length / 7) : 1;

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((fraction) => fraction * yMax);

  const ariaLabel =
    accessibleLabel ?? `Sleep split bars, ${bars.length} days (night vs day)`;

  return (
    <div ref={containerRef} className={styles.container}>
      {chartWidth > 0 && (
        <svg
          width={chartWidth}
          height={height}
          className={styles.svg}
          role="img"
          aria-label={ariaLabel}
        >
          <title>{ariaLabel}</title>

          {ticks.map((tickValue, index) => (
            <g key={`gridline-${index}`} aria-hidden>
              <line
                x1={paddingLeft}
                x2={chartWidth - paddingRight}
                y1={yAt(tickValue)}
                y2={yAt(tickValue)}
                stroke="var(--hairline)"
                strokeWidth={index === 0 ? 1 : 0.75}
                strokeDasharray={index === 0 ? "" : "1.5 4"}
              />
              <text
                x={paddingLeft - 6}
                y={yAt(tickValue) + 3}
                textAnchor="end"
                fontFamily="var(--font-jetbrains-mono), ui-monospace, monospace"
                fontSize="9"
                fill="var(--muted-2)"
              >
                {tickValue === 0 ? "0" : `${Math.round(tickValue / 60)}h`}
              </text>
            </g>
          ))}

          {bars.map((bar, index) => {
            const xLeft = paddingLeft + index * slotWidth + (slotWidth - barWidth) / 2;
            const nightTop = yAt(bar.nightMinutes);
            const nightHeight = Math.max(0, paddingTop + innerHeight - nightTop);
            const dayBottom = nightTop;
            const dayTop = yAt(bar.nightMinutes + bar.dayMinutes);
            const dayHeight = Math.max(0, dayBottom - dayTop);
            const total = bar.nightMinutes + bar.dayMinutes;
            const tooltip = `${bar.dayLabel} — ${formatHoursMinutes(total)} total · ${formatHoursMinutes(bar.nightMinutes)} night · ${formatHoursMinutes(bar.dayMinutes)} day`;
            const showLabel = index % labelStride === 0 || index === bars.length - 1;
            return (
              <g key={`bar-${bar.date}-${reactId}`}>
                <title>{tooltip}</title>
                {nightHeight > 0 && (
                  <rect
                    x={xLeft}
                    y={nightTop}
                    width={barWidth}
                    height={nightHeight}
                    fill="var(--blue-midnight)"
                    rx="2"
                  />
                )}
                {dayHeight > 0 && (
                  <rect
                    x={xLeft}
                    y={dayTop}
                    width={barWidth}
                    height={dayHeight}
                    fill="color-mix(in srgb, var(--blue-midnight) 35%, var(--paper))"
                    rx="2"
                  />
                )}
                {showLabel && (
                  <text
                    x={xLeft + barWidth / 2}
                    y={paddingTop + innerHeight + 14}
                    textAnchor="middle"
                    fontFamily="var(--font-jetbrains-mono), ui-monospace, monospace"
                    fontSize="9"
                    fill="var(--muted-2)"
                  >
                    {bar.dayLabel}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      )}

      <div className={`${styles.legend} mono`}>
        <span className={styles.legendItem}>
          <span className={styles.swatchNight} aria-hidden />
          night
        </span>
        <span className={styles.legendItem}>
          <span className={styles.swatchDay} aria-hidden />
          day naps
        </span>
      </div>
    </div>
  );
}
