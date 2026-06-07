import { useId } from "react";
import styles from "./ActivityRing.module.css";

function roundToTwoDecimals(value: number): number {
  return Math.round(value * 100) / 100;
}

type ActivityRingProps = {
  /** Raw percentage (0..∞). Visual fill caps at 100; values above shift color. */
  percent?: number;
  size?: number;
  label?: string;
  sublabel?: string;
  color?: string;
  /** Stroke color when the goal is exceeded. */
  exceededColor?: string;
  accessibleLabel?: string;
};

export function ActivityRing({
  percent = 0,
  size = 220,
  label = "0%",
  sublabel = "of daily goal",
  color = "var(--warm)",
  exceededColor = "var(--status-positive)",
  accessibleLabel,
}: ActivityRingProps) {
  const reactId = useId().replace(/[^a-z0-9]/gi, "");
  const gradientId = `ring-${reactId}-outer`;
  const glowId = `ring-${reactId}-glow`;

  const isOverGoal = percent > 100;
  const visualPercent = Math.min(Math.max(percent, 0), 100);
  const strokeColor = isOverGoal ? exceededColor : color;

  const centerX = size / 2;
  const centerY = size / 2;
  const stroke = size * 0.08;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const filled = (visualPercent / 100) * circumference;

  const tipAngle = (visualPercent / 100) * 2 * Math.PI - Math.PI / 2;
  const tipX = roundToTwoDecimals(centerX + radius * Math.cos(tipAngle));
  const tipY = roundToTwoDecimals(centerY + radius * Math.sin(tipAngle));

  const ariaLabel = accessibleLabel ?? `Activity ring: ${label} ${sublabel}`;

  return (
    <div className={styles.wrapper} style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-label={ariaLabel}
      >
        <title>{ariaLabel}</title>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={strokeColor} stopOpacity="0.9" />
            <stop offset="100%" stopColor={strokeColor} stopOpacity="1" />
          </linearGradient>
          <radialGradient id={glowId} cx="0.5" cy="0.5" r="0.5">
            <stop offset="55%" stopColor={strokeColor} stopOpacity="0" />
            <stop offset="100%" stopColor={strokeColor} stopOpacity="0.15" />
          </radialGradient>
        </defs>

        <circle aria-hidden cx={centerX} cy={centerY} r={radius} fill={`url(#${glowId})`} />

        <g aria-hidden transform={`rotate(-90 ${centerX} ${centerY})`}>
          <circle
            cx={centerX}
            cy={centerY}
            r={radius}
            fill="none"
            stroke="var(--paper-on-dark-track)"
            strokeWidth={stroke}
          />
          <circle
            cx={centerX}
            cy={centerY}
            r={radius}
            fill="none"
            stroke={`url(#${gradientId})`}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${filled} ${circumference - filled}`}
          />
        </g>

        <circle
          aria-hidden
          cx={tipX}
          cy={tipY}
          r={stroke * 0.55}
          fill="var(--paper-on-dark-warm)"
        />
        <circle aria-hidden cx={tipX} cy={tipY} r={stroke * 0.32} fill={strokeColor} />
      </svg>

      <div className={styles.center} style={{ color: "var(--paper-on-dark-warm)" }}>
        <div className={`${styles.centerLabel} display`} style={{ fontSize: size * 0.22 }}>
          {label}
        </div>
        <div className={styles.centerSublabel}>{sublabel}</div>
      </div>
    </div>
  );
}
