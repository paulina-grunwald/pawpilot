import { useId } from "react";
import styles from "./Sparkline.module.css";

type SparklineProps = {
  values: number[];
  width?: number;
  height?: number;
  color?: string;
  fill?: boolean;
  accessibleLabel?: string;
};

const PADDING = 3;

export function Sparkline({
  values,
  width = 120,
  height = 32,
  color = "var(--warm)",
  fill = true,
  accessibleLabel,
}: SparklineProps) {
  const reactId = useId().replace(/[^a-z0-9]/gi, "");
  const fillId = `spark-${reactId}`;

  if (values.length < 2) {
    return <div className={styles.empty} style={{ width, height }} aria-hidden />;
  }

  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const span = maximum - minimum || 1;
  const innerWidth = width - PADDING * 2;
  const innerHeight = height - PADDING * 2;

  const xAt = (index: number) => PADDING + (index / (values.length - 1)) * innerWidth;
  const yAt = (value: number) => PADDING + (1 - (value - minimum) / span) * innerHeight;

  const linePath = values
    .map((value, index) => `${index === 0 ? "M" : "L"}${xAt(index)},${yAt(value)}`)
    .join(" ");
  const lastIndex = values.length - 1;
  const areaPath = `${linePath} L${xAt(lastIndex)},${height - PADDING} L${xAt(0)},${height - PADDING} Z`;

  const ariaLabel = accessibleLabel ?? `Sparkline, latest value ${values[lastIndex]}`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={ariaLabel}
      className={styles.svg}
    >
      <title>{ariaLabel}</title>
      {fill && (
        <defs>
          <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.28" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
      )}
      {fill && <path aria-hidden d={areaPath} fill={`url(#${fillId})`} />}
      <path
        aria-hidden
        d={linePath}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle aria-hidden cx={xAt(lastIndex)} cy={yAt(values[lastIndex])} r="2" fill={color} />
    </svg>
  );
}
