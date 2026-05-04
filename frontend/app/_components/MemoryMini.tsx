type MemoryItem = {
  date: string;
  text: string;
  tone: "forest" | "muted" | "terracotta" | "ochre";
};

const items: MemoryItem[] = [
  { date: "Mar 2024", text: "Hip dysplasia dx · L side", tone: "forest" },
  { date: "Jun 2024", text: "Bordetella booster", tone: "muted" },
  { date: "Sep 2024", text: "Allergic flare — chicken", tone: "terracotta" },
  { date: "Now", text: "Activity ↓ 38%", tone: "ochre" },
];

const toneBg: Record<MemoryItem["tone"], string> = {
  forest: "var(--forest)",
  muted: "var(--hairline-strong)",
  terracotta: "var(--terracotta)",
  ochre: "var(--ochre)",
};

export function MemoryMini() {
  return (
    <div style={{ marginTop: 18, position: "relative" }}>
      <div
        style={{
          position: "absolute",
          left: 7,
          top: 6,
          bottom: 6,
          width: 1.5,
          background:
            "repeating-linear-gradient(180deg, var(--hairline-strong) 0 4px, transparent 4px 8px)",
        }}
      />
      {items.map((memory, index) => (
        <div
          key={index}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 14,
            marginBottom: index === items.length - 1 ? 0 : 10,
            position: "relative",
          }}
        >
          <span
            style={{
              width: 16,
              height: 16,
              borderRadius: "50%",
              background: toneBg[memory.tone],
              border: "3px solid var(--surface)",
              zIndex: 1,
              flexShrink: 0,
            }}
          />
          <span
            className="mono"
            style={{
              fontSize: 10.5,
              color: "var(--muted)",
              letterSpacing: "0.04em",
              minWidth: 64,
            }}
          >
            {memory.date}
          </span>
          <span style={{ fontSize: 12.5, color: "var(--ink)" }}>
            {memory.text}
          </span>
        </div>
      ))}
    </div>
  );
}
