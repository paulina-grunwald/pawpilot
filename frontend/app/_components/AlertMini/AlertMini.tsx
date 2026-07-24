import { BellIcon } from "../icons";

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
    <div className="mt-[18px] flex flex-col gap-2">
      {items.map((alert, index) => (
        <div
          key={index}
          className="flex items-center gap-3 rounded-[10px] px-3 py-2"
          style={{
            background: alert.strong
              ? "color-mix(in srgb, var(--ochre) 10%, transparent)"
              : "transparent",
            border: alert.strong
              ? "1px solid color-mix(in srgb, var(--ochre) 35%, transparent)"
              : "1px solid transparent",
          }}
        >
          <span
            className="mono min-w-[28px] text-[9px] font-semibold tracking-[0.08em]"
            style={{ color: toneColor[alert.tone] }}
          >
            {alert.time}
          </span>
          <span
            className="text-ink flex-1 text-[12.5px]"
            style={{ fontWeight: alert.strong ? 600 : 400 }}
          >
            {alert.text}
          </span>
          {alert.strong && <BellIcon size={14} color="var(--ochre)" />}
        </div>
      ))}
    </div>
  );
}
