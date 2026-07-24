"use client";

import { useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import styles from "./LineChart.module.css";

const DEFAULT_DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"] as const;

type LineChartProps = {
  values: number[];
  height?: number;
  color?: string;
  days?: readonly string[];
  dates?: readonly (string | number)[];
  baseline?: { low: number; high: number };
  mean?: number;
  goal?: number;
  yTicks?: number;
  yFormat?: (value: number) => string;
  unit?: string;
  compact?: boolean;
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

type LegendSwatchProps = {
  type: "solid" | "dash" | "hatch";
  color?: string;
  children: ReactNode;
};

function LegendSwatch({ type, color = "var(--muted)", children }: LegendSwatchProps) {
  const hatchId = `legend-hatch-${useId().replace(/[^a-z0-9]/gi, "")}`;
  return (
    <span className={styles.legendSwatch}>
      <svg aria-hidden width="18" height="8" style={{ display: "block" }}>
        {type === "hatch" && (
          <defs>
            <pattern
              id={hatchId}
              patternUnits="userSpaceOnUse"
              width="4"
              height="4"
              patternTransform="rotate(45)"
            >
              <line
                x1="0"
                y1="0"
                x2="0"
                y2="4"
                stroke="var(--muted-2)"
                strokeWidth="0.6"
                strokeOpacity="0.5"
              />
            </pattern>
          </defs>
        )}
        {type === "solid" && (
          <line
            x1="0"
            x2="18"
            y1="4"
            y2="4"
            stroke={color}
            strokeWidth="1.75"
            strokeLinecap="round"
          />
        )}
        {type === "dash" && (
          <line
            x1="0"
            x2="18"
            y1="4"
            y2="4"
            stroke={color}
            strokeWidth="1.25"
            strokeDasharray="3 2"
          />
        )}
        {type === "hatch" && (
          <rect
            x="0"
            y="1"
            width="18"
            height="6"
            fill={`url(#${hatchId})`}
            stroke="var(--muted-2)"
            strokeOpacity="0.5"
            strokeWidth="0.5"
            strokeDasharray="1 1.5"
          />
        )}
      </svg>
      {children}
    </span>
  );
}

export function LineChart({
  values,
  height = 180,
  color = "var(--warm)",
  days = DEFAULT_DAYS,
  dates,
  baseline,
  mean,
  goal,
  yTicks = 4,
  yFormat = (value) => String(value),
  unit = "",
  compact = false,
  accessibleLabel,
}: LineChartProps) {
  const [containerRef, fullWidth] = useMeasuredWidth();
  const reactId = useId().replace(/[^a-z0-9]/gi, "");
  const fillId = `line-${reactId}-fill`;
  const hatchPatternId = `line-${reactId}-hatch`;

  if (values.length < 2) {
    return <div ref={containerRef} className={styles.container} aria-hidden />;
  }

  const chartWidth = Math.max(fullWidth, 240);
  const paddingLeft = compact ? 10 : 38;
  const paddingRight = 54;
  const paddingTop = 18;
  const paddingBottom = dates ? 32 : 22;
  const innerWidth = chartWidth - paddingLeft - paddingRight;
  const innerHeight = height - paddingTop - paddingBottom;

  const allValues: number[] = [...values];
  if (baseline) allValues.push(baseline.low, baseline.high);
  if (goal != null) allValues.push(goal);
  if (mean != null) allValues.push(mean);

  const minOfValues = allValues.reduce((acc, value) => (value < acc ? value : acc), Infinity);
  const maxOfValues = allValues.reduce((acc, value) => (value > acc ? value : acc), -Infinity);
  const span = maxOfValues - minOfValues || 1;
  const yMin = Math.max(0, minOfValues - span * 0.18);
  const yMax = maxOfValues + span * 0.18;

  const xAt = (index: number) => paddingLeft + (index / (values.length - 1)) * innerWidth;
  const yAt = (value: number) => paddingTop + (1 - (value - yMin) / (yMax - yMin)) * innerHeight;

  const ticks = Array.from(
    { length: yTicks + 1 },
    (_, tickIndex) => yMin + (tickIndex / yTicks) * (yMax - yMin),
  );
  const linePath = values
    .map((value, index) => `${index === 0 ? "M" : "L"}${xAt(index)},${yAt(value)}`)
    .join(" ");
  const todayIndex = values.length - 1;
  const todayY = yAt(values[todayIndex]);
  const todayX = xAt(todayIndex);
  const calloutAbove = todayY - paddingTop > 22;
  const calloutY = calloutAbove ? todayY - 22 : todayY + 6;

  const ariaLabel =
    accessibleLabel ?? `Line chart: latest value ${yFormat(values[todayIndex])}${unit}`;

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
          <defs>
            <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.22" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </linearGradient>
            <pattern
              id={hatchPatternId}
              patternUnits="userSpaceOnUse"
              width="5"
              height="5"
              patternTransform="rotate(45)"
            >
              <line
                x1="0"
                y1="0"
                x2="0"
                y2="5"
                stroke="var(--muted-2)"
                strokeWidth="0.6"
                strokeOpacity="0.4"
              />
            </pattern>
          </defs>

          {ticks.map((tickValue, tickIndex) => (
            <g key={`gridline-${tickIndex}`} aria-hidden>
              <line
                x1={paddingLeft}
                x2={chartWidth - paddingRight + 2}
                y1={yAt(tickValue)}
                y2={yAt(tickValue)}
                stroke="var(--hairline)"
                strokeWidth={tickIndex === 0 ? 1 : 0.75}
                strokeDasharray={tickIndex === 0 ? "" : "1.5 4"}
              />
              {!compact && (
                <text
                  x={paddingLeft - 8}
                  y={yAt(tickValue) + 3}
                  textAnchor="end"
                  fontFamily="var(--font-jetbrains-mono), ui-monospace, monospace"
                  fontSize="9"
                  fill="var(--muted-2)"
                  letterSpacing="0.04em"
                >
                  {yFormat(Math.round(tickValue))}
                </text>
              )}
            </g>
          ))}

          {baseline && (
            <g aria-hidden>
              <rect
                x={paddingLeft}
                y={yAt(baseline.high)}
                width={innerWidth}
                height={Math.max(0, yAt(baseline.low) - yAt(baseline.high))}
                fill={`url(#${hatchPatternId})`}
              />
              <line
                x1={paddingLeft}
                x2={chartWidth - paddingRight}
                y1={yAt(baseline.high)}
                y2={yAt(baseline.high)}
                stroke="var(--muted-2)"
                strokeOpacity="0.5"
                strokeWidth="0.75"
                strokeDasharray="1 2"
              />
              <line
                x1={paddingLeft}
                x2={chartWidth - paddingRight}
                y1={yAt(baseline.low)}
                y2={yAt(baseline.low)}
                stroke="var(--muted-2)"
                strokeOpacity="0.5"
                strokeWidth="0.75"
                strokeDasharray="1 2"
              />
            </g>
          )}

          {mean != null && (
            <line
              aria-hidden
              x1={paddingLeft}
              x2={chartWidth - paddingRight}
              y1={yAt(mean)}
              y2={yAt(mean)}
              stroke="var(--muted)"
              strokeWidth="1"
              strokeDasharray="4 3"
            />
          )}

          {goal != null && (
            <g aria-hidden>
              <line
                x1={paddingLeft}
                x2={chartWidth - paddingRight}
                y1={yAt(goal)}
                y2={yAt(goal)}
                stroke={color}
                strokeWidth="1.25"
                strokeDasharray="3 3"
                strokeOpacity="0.75"
              />
              <text
                x={chartWidth - paddingRight + 4}
                y={yAt(goal) + 3}
                fontFamily="var(--font-jetbrains-mono), ui-monospace, monospace"
                fontSize="9"
                fill={color}
                letterSpacing="0.04em"
              >
                goal {yFormat(goal)}
              </text>
            </g>
          )}

          <path
            aria-hidden
            d={`${linePath} L${xAt(todayIndex)},${paddingTop + innerHeight} L${xAt(0)},${paddingTop + innerHeight} Z`}
            fill={`url(#${fillId})`}
          />
          <path
            aria-hidden
            d={linePath}
            fill="none"
            stroke={color}
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          <line
            aria-hidden
            x1={todayX}
            x2={todayX}
            y1={paddingTop}
            y2={paddingTop + innerHeight}
            stroke={color}
            strokeWidth="0.75"
            strokeDasharray="2 3"
            strokeOpacity="0.45"
          />

          {values.map((value, index) => (
            <g key={`datapoint-${index}`} aria-hidden>
              {index === todayIndex && (
                <circle cx={xAt(index)} cy={yAt(value)} r="9" fill={color} fillOpacity="0.16" />
              )}
              <circle
                cx={xAt(index)}
                cy={yAt(value)}
                r={index === todayIndex ? 4 : 2.5}
                fill="var(--card)"
                stroke={color}
                strokeWidth={index === todayIndex ? 2 : 1.5}
              />
            </g>
          ))}

          <g aria-hidden>
            <rect
              x={Math.min(todayX + 8, chartWidth - paddingRight - 46)}
              y={calloutY - 12}
              rx="3"
              ry="3"
              width={50}
              height={20}
              fill="var(--card)"
              stroke="var(--hairline-strong)"
              strokeWidth="0.75"
            />
            <text
              x={Math.min(todayX + 8, chartWidth - paddingRight - 46) + 7}
              y={calloutY + 2}
              fontFamily="var(--font-fraunces), Georgia, serif"
              fontSize="12"
              fontWeight="500"
              fill="var(--ink-deep)"
              letterSpacing="-0.01em"
            >
              {yFormat(values[todayIndex])}
              {unit}
            </text>
          </g>

          <line
            aria-hidden
            x1={paddingLeft}
            x2={chartWidth - paddingRight}
            y1={paddingTop + innerHeight + 2}
            y2={paddingTop + innerHeight + 2}
            stroke="var(--hairline-strong)"
            strokeWidth="0.75"
          />
          {values.map((_, index) => (
            <g key={`xtick-${index}`} aria-hidden>
              <line
                x1={xAt(index)}
                x2={xAt(index)}
                y1={paddingTop + innerHeight + 2}
                y2={paddingTop + innerHeight + 5}
                stroke="var(--hairline-strong)"
                strokeWidth="0.75"
              />
              <text
                x={xAt(index)}
                y={paddingTop + innerHeight + 15}
                textAnchor="middle"
                fontFamily="var(--font-jetbrains-mono), ui-monospace, monospace"
                fontSize="10"
                fontWeight={index === todayIndex ? 600 : 400}
                fill={
                  index === todayIndex
                    ? "var(--ink-deep)"
                    : index >= 5
                      ? "var(--ochre)"
                      : "var(--muted-2)"
                }
                letterSpacing="0.04em"
              >
                {days[index] ?? String(index + 1)}
              </text>
              {dates && (
                <text
                  x={xAt(index)}
                  y={paddingTop + innerHeight + 26}
                  textAnchor="middle"
                  fontFamily="var(--font-jetbrains-mono), ui-monospace, monospace"
                  fontSize="9"
                  fill="var(--muted-2)"
                >
                  {dates[index]}
                </text>
              )}
            </g>
          ))}
        </svg>
      )}

      {!compact && (
        <div className={`${styles.legend} mono`} style={{ paddingLeft }}>
          <LegendSwatch type="solid" color={color}>
            this week
          </LegendSwatch>
          {mean != null && (
            <LegendSwatch type="dash" color="var(--muted)">
              30-day mean
            </LegendSwatch>
          )}
          {baseline && <LegendSwatch type="hatch">baseline range</LegendSwatch>}
          {goal != null && (
            <LegendSwatch type="dash" color={color}>
              goal
            </LegendSwatch>
          )}
        </div>
      )}
    </div>
  );
}
