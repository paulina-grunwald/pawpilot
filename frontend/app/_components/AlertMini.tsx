import { BellIcon } from "./icons";

type AlertItem = {
  time: string;
  text: string;
  tone: "muted" | "ochre" | "forest";
  strong?: boolean;
};

const items: AlertItem[] = [
  { time: "TUE", text: "Sleep ↑ 22% · worth noting", tone: "muted" },
  { time: "WED", text: "Activity ↓ 38% · 3-day window", tone: "ochre", strong: true },
  { time: "THU", text: "Heart rate variance normal", tone: "forest" },
];

const toneColor: Record<AlertItem["tone"], string> = {
  muted: "var(--muted)",
  ochre: "var(--ochre)",
  forest: "var(--forest)",
};

export function AlertMini() {
  return (
    <div style={{ marginTop: 18, display: "flex", flexDirection: "column", gap: 8 }}>
      {items.map((alert, index) => (
        <div
          key={index}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "8px 12px",
            borderRadius: 10,
            background: alert.strong ? "rgba(200,132,30,0.10)" : "transparent",
            border: alert.strong
              ? "1px solid rgba(200,132,30,0.35)"
              : "1px solid transparent",
          }}
        >
          <span
            className="mono"
            style={{
              fontSize: 9,
              fontWeight: 600,
              color: toneColor[alert.tone],
              letterSpacing: "0.08em",
              minWidth: 28,
            }}
          >
            {alert.time}
          </span>
          <span
            style={{
              fontSize: 12.5,
              color: "var(--ink)",
              flex: 1,
              fontWeight: alert.strong ? 600 : 400,
            }}
          >
            {alert.text}
          </span>
          {alert.strong && (
            <BellIcon width={14} height={14} style={{ color: "var(--ochre)" }} />
          )}
        </div>
      ))}
    </div>
  );
}
