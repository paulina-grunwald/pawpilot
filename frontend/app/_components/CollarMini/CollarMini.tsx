const BAR_COUNT = 24;

export function CollarMini() {
  return (
    <div className="mt-[18px] rounded-[14px] border border-(--hairline) bg-(--paper) p-[14px]">
      <div className="mb-[10px] flex items-center justify-between">
        <span className="mono text-muted text-[10px] tracking-[0.06em] uppercase">
          Live · last 24h
        </span>
        <span className="text-forest inline-flex items-center gap-[5px] text-[11px] font-semibold">
          <span
            className="bg-forest h-[6px] w-[6px] rounded-full"
            style={{ animation: "pulse-dot 1.4s infinite" }}
          />
          Synced
        </span>
      </div>
      <div className="flex h-11 items-end gap-[3px]">
        {Array.from({ length: BAR_COUNT }, (_, index) => {
          const heightPx = 8 + Math.sin(index * 0.5) * 12 + Math.cos(index * 0.9) * 8 + 18;
          const isActive = index >= 14 && index <= 19;
          return (
            <div
              key={index}
              className="rounded-[2px]"
              style={{
                flex: 1,
                height: heightPx,
                background: isActive ? "var(--terracotta)" : "var(--hairline-strong)",
                opacity: isActive ? 1 : 0.7,
              }}
            />
          );
        })}
      </div>
      <div className="mt-[6px] flex justify-between">
        <span className="mono text-muted text-[10px]">00:00</span>
        <span className="mono text-terracotta text-[10px] font-semibold">walk · 18 min</span>
        <span className="mono text-muted text-[10px]">now</span>
      </div>
    </div>
  );
}
