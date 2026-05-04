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
    <div className="mt-[18px] relative">
      <div
        className="absolute left-[7px] top-[6px] bottom-[6px] w-[1.5px]"
        style={{
          background:
            "repeating-linear-gradient(180deg, var(--hairline-strong) 0 4px, transparent 4px 8px)",
        }}
      />
      {items.map((memory, index) => (
        <div
          key={index}
          className="flex items-center gap-[14px] relative"
          style={{ marginBottom: index === items.length - 1 ? 0 : 10 }}
        >
          <span
            className="w-4 h-4 rounded-full border-[3px] border-surface z-[1] shrink-0"
            style={{ background: toneBg[memory.tone] }}
          />
          <span className="mono text-[10.5px] text-muted tracking-[0.04em] min-w-[64px]">
            {memory.date}
          </span>
          <span className="text-[12.5px] text-ink">
            {memory.text}
          </span>
        </div>
      ))}
    </div>
  );
}
