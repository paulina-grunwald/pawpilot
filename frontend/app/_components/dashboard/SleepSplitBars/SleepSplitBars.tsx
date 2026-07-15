"use client";

import {
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { placeTooltip, pointerToIndex } from "../chartGeometry";
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

const DAY_NAP_FILL = "color-mix(in srgb, var(--blue-midnight) 35%, var(--paper))";

export function SleepSplitBars({ bars, height = 200, accessibleLabel }: SleepSplitBarsProps) {
  const [containerRef, fullWidth] = useMeasuredWidth();
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
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

  const handlePointerMove = (event: ReactPointerEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const bounds = svg.getBoundingClientRect();
    setHoverIndex(
      pointerToIndex({
        clientX: event.clientX,
        boundsLeft: bounds.left,
        boundsWidth: bounds.width,
        chartWidth,
        paddingLeft,
        innerWidth,
        count: bars.length,
        snap: "floor",
      }),
    );
  };

  const hoveredBar = hoverIndex !== null ? bars[hoverIndex] : null;
  const tooltipLines = hoveredBar
    ? [
        {
          text: `${hoveredBar.dayLabel} · ${formatHoursMinutes(hoveredBar.nightMinutes + hoveredBar.dayMinutes)}`,
          color: "var(--ink-deep)",
        },
        { text: `night ${formatHoursMinutes(hoveredBar.nightMinutes)}`, color: "var(--blue-midnight)" },
        { text: `day naps ${formatHoursMinutes(hoveredBar.dayMinutes)}`, color: "var(--muted)" },
      ]
    : [];
  const tooltipWidth = Math.max(
    88,
    ...tooltipLines.map((line) => line.text.length * 6.2 + 18),
  );
  const tooltipHeight = 50;
  const { x: tooltipX, y: tooltipY } =
    hoveredBar !== null && hoverIndex !== null
      ? placeTooltip({
          pointX: paddingLeft + hoverIndex * slotWidth + slotWidth / 2,
          pointY: yAt(hoveredBar.nightMinutes + hoveredBar.dayMinutes),
          width: tooltipWidth,
          height: tooltipHeight,
          chartWidth,
          paddingLeft,
          paddingRight,
          paddingTop,
          offset: 8,
          overflow: "clamp",
        })
      : { x: 0, y: 0 };

  return (
    <div ref={containerRef} className={styles.container}>
      {chartWidth > 0 && (
        <svg
          ref={svgRef}
          width={chartWidth}
          height={height}
          className={styles.svg}
          role="img"
          aria-label={ariaLabel}
          onPointerMove={handlePointerMove}
          onPointerLeave={() => setHoverIndex(null)}
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
            const isDimmed = hoverIndex !== null && hoverIndex !== index;
            return (
              <g key={`bar-${bar.date}-${reactId}`} opacity={isDimmed ? 0.45 : 1}>
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
                    fill={DAY_NAP_FILL}
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

          {hoveredBar && (
            <g aria-hidden>
              <rect
                x={tooltipX}
                y={tooltipY}
                rx="4"
                ry="4"
                width={tooltipWidth}
                height={tooltipHeight}
                fill="var(--card)"
                stroke="var(--hairline-strong)"
                strokeWidth="0.75"
              />
              {tooltipLines.map((line, lineIndex) => (
                <text
                  key={`tooltip-line-${lineIndex}`}
                  x={tooltipX + 10}
                  y={tooltipY + 15 + lineIndex * 13}
                  fontFamily={
                    lineIndex === 0
                      ? "var(--font-fraunces), Georgia, serif"
                      : "var(--font-jetbrains-mono), ui-monospace, monospace"
                  }
                  fontSize={lineIndex === 0 ? "11" : "10"}
                  fontWeight={lineIndex === 0 ? "500" : "400"}
                  fill={line.color}
                  letterSpacing="0.02em"
                >
                  {line.text}
                </text>
              ))}
            </g>
          )}
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
