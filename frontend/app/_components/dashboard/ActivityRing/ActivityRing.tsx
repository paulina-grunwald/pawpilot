import { useId } from "react";
import styles from "./ActivityRing.module.css";

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

type ActivityRingProps = {
  percent?: number;
  innerPercent?: number;
  size?: number;
  label?: string;
  sublabel?: string;
  color?: string;
  innerColor?: string;
  accessibleLabel?: string;
};

export function ActivityRing({
  percent = 78,
  innerPercent = 64,
  size = 220,
  label = "78%",
  sublabel = "of daily goal",
  color = "var(--warm)",
  innerColor = "var(--warm-light)",
  accessibleLabel,
}: ActivityRingProps) {
  const reactId = useId().replace(/[^a-z0-9]/gi, "");
  const gradientId = `ring-${reactId}-outer`;
  const innerGradientId = `ring-${reactId}-inner`;
  const glowId = `ring-${reactId}-glow`;

  const centerX = size / 2;
  const centerY = size / 2;
  const stroke = size * 0.075;
  const innerGap = size * 0.045;
  const outerRadius = (size - stroke) / 2;
  const innerRadius = outerRadius - stroke - innerGap;
  const outerCircumference = 2 * Math.PI * outerRadius;
  const innerCircumference = 2 * Math.PI * innerRadius;
  const filledOuter = (percent / 100) * outerCircumference;
  const filledInner = (innerPercent / 100) * innerCircumference;

  const tipAngle = (percent / 100) * 2 * Math.PI - Math.PI / 2;
  const tipX = round2(centerX + outerRadius * Math.cos(tipAngle));
  const tipY = round2(centerY + outerRadius * Math.sin(tipAngle));

  const ticks = Array.from({ length: 24 }, (_, tickIndex) => {
    const angle = (tickIndex / 24) * 2 * Math.PI - Math.PI / 2;
    const innerTickRadius = outerRadius + stroke * 0.75;
    const outerTickRadius = innerTickRadius + (tickIndex % 6 === 0 ? 8 : 4);
    return {
      x1: round2(centerX + innerTickRadius * Math.cos(angle)),
      y1: round2(centerY + innerTickRadius * Math.sin(angle)),
      x2: round2(centerX + outerTickRadius * Math.cos(angle)),
      y2: round2(centerY + outerTickRadius * Math.sin(angle)),
      strong: tickIndex % 6 === 0,
    };
  });

  const hourLabels = [
    { text: "12a", x: centerX, y: centerY - outerRadius - stroke * 0.75 - 16, anchor: "middle" as const },
    { text: "6a", x: centerX + outerRadius + stroke * 0.75 + 14, y: centerY + 4, anchor: "start" as const },
    { text: "12p", x: centerX, y: centerY + outerRadius + stroke * 0.75 + 18, anchor: "middle" as const },
    { text: "6p", x: centerX - outerRadius - stroke * 0.75 - 14, y: centerY + 4, anchor: "end" as const },
  ];

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
            <stop offset="0%" stopColor={color} stopOpacity="0.9" />
            <stop offset="100%" stopColor={color} stopOpacity="1" />
          </linearGradient>
          <linearGradient id={innerGradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={innerColor} stopOpacity="0.85" />
            <stop offset="100%" stopColor={innerColor} stopOpacity="1" />
          </linearGradient>
          <radialGradient id={glowId} cx="0.5" cy="0.5" r="0.5">
            <stop offset="55%" stopColor={color} stopOpacity="0" />
            <stop offset="100%" stopColor={color} stopOpacity="0.15" />
          </radialGradient>
        </defs>

        <circle aria-hidden cx={centerX} cy={centerY} r={outerRadius} fill={`url(#${glowId})`} />

        <g aria-hidden>
          {ticks.map((tick, tickIndex) => (
            <line
              key={tickIndex}
              x1={tick.x1}
              y1={tick.y1}
              x2={tick.x2}
              y2={tick.y2}
              stroke={tick.strong ? "var(--paper-on-dark-sub)" : "var(--paper-on-dark-faint)"}
              strokeWidth={tick.strong ? 1.5 : 1}
              strokeLinecap="round"
            />
          ))}
        </g>

        {hourLabels.map((hourLabel, labelIndex) => (
          <text
            key={labelIndex}
            aria-hidden
            x={hourLabel.x}
            y={hourLabel.y}
            textAnchor={hourLabel.anchor}
            fontFamily="var(--font-jetbrains-mono), ui-monospace, monospace"
            fontSize="9"
            fill="var(--paper-on-dark-mid)"
            letterSpacing="0.04em"
          >
            {hourLabel.text}
          </text>
        ))}

        <g aria-hidden transform={`rotate(-90 ${centerX} ${centerY})`}>
          <circle
            cx={centerX}
            cy={centerY}
            r={outerRadius}
            fill="none"
            stroke="var(--paper-on-dark-track)"
            strokeWidth={stroke}
          />
          <circle
            cx={centerX}
            cy={centerY}
            r={outerRadius}
            fill="none"
            stroke={`url(#${gradientId})`}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${filledOuter} ${outerCircumference - filledOuter}`}
          />
          <circle
            cx={centerX}
            cy={centerY}
            r={innerRadius}
            fill="none"
            stroke="var(--paper-on-dark-track)"
            strokeWidth={stroke * 0.7}
          />
          <circle
            cx={centerX}
            cy={centerY}
            r={innerRadius}
            fill="none"
            stroke={`url(#${innerGradientId})`}
            strokeWidth={stroke * 0.7}
            strokeLinecap="round"
            strokeDasharray={`${filledInner} ${innerCircumference - filledInner}`}
            opacity={0.95}
          />
        </g>

        <circle aria-hidden cx={tipX} cy={tipY} r={stroke * 0.55} fill="var(--paper-on-dark-warm)" />
        <circle aria-hidden cx={tipX} cy={tipY} r={stroke * 0.32} fill={color} />
      </svg>

      <div className={styles.center} style={{ color: "var(--paper-on-dark-warm)" }}>
        <div
          className={`${styles.centerLabel} display`}
          style={{ fontSize: size * 0.22 }}
        >
          {label}
        </div>
        <div className={styles.centerSublabel}>{sublabel}</div>
        <div className={`${styles.centerLegend} mono`}>
          <span className={styles.legendItem}>
            <span className={styles.legendDot} style={{ background: color }} />
            move
          </span>
          <span className={styles.legendItem}>
            <span className={styles.legendDot} style={{ background: innerColor }} />
            active
          </span>
        </div>
      </div>
    </div>
  );
}
