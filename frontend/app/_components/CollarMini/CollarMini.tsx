const BAR_COUNT = 24;

export function CollarMini() {
  return (
    <div className="mt-[18px] p-[14px] bg-(--paper) rounded-[14px] border border-(--hairline)">
      <div className="flex justify-between items-center mb-[10px]">
        <span className="mono text-[10px] text-muted tracking-[0.06em] uppercase">
          Live · last 24h
        </span>
        <span className="inline-flex items-center gap-[5px] text-[11px] text-forest font-semibold">
          <span
            className="w-[6px] h-[6px] rounded-full bg-forest"
            style={{ animation: "pulse-dot 1.4s infinite" }}
          />
          Synced
        </span>
      </div>
      <div className="flex items-end gap-[3px] h-11">
        {Array.from({ length: BAR_COUNT }, (_, index) => {
          const heightPx =
            8 + Math.sin(index * 0.5) * 12 + Math.cos(index * 0.9) * 8 + 18;
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
      <div className="flex justify-between mt-[6px]">
        <span className="mono text-[10px] text-muted">00:00</span>
        <span className="mono text-[10px] text-terracotta font-semibold">
          walk · 18 min
        </span>
        <span className="mono text-[10px] text-muted">now</span>
      </div>
    </div>
  );
}
