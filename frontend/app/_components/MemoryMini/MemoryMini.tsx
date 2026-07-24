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
    <div className="relative mt-[18px]">
      <div
        className="absolute top-[6px] bottom-[6px] left-[7px] w-[1.5px]"
        style={{
          background:
            "repeating-linear-gradient(180deg, var(--hairline-strong) 0 4px, transparent 4px 8px)",
        }}
      />
      {items.map((memory, index) => (
        <div
          key={index}
          className="relative flex items-center gap-[14px]"
          style={{ marginBottom: index === items.length - 1 ? 0 : 10 }}
        >
          <span
            className="border-surface z-[1] h-4 w-4 shrink-0 rounded-full border-[3px]"
            style={{ background: toneBg[memory.tone] }}
          />
          <span className="mono text-muted min-w-[64px] text-[10.5px] tracking-[0.04em]">
            {memory.date}
          </span>
          <span className="text-ink text-[12.5px]">{memory.text}</span>
        </div>
      ))}
    </div>
  );
}
