const BAR_COUNT = 24;

export function CollarMini() {
  return (
    <div
      style={{
        marginTop: 18,
        padding: 14,
        background: "var(--paper)",
        borderRadius: 14,
        border: "1px solid var(--hairline)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 10,
        }}
      >
        <span
          className="mono"
          style={{
            fontSize: 10,
            color: "var(--muted)",
            letterSpacing: "0.06em",
            textTransform: "uppercase",
          }}
        >
          Live · last 24h
        </span>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 5,
            fontSize: 11,
            color: "var(--forest)",
            fontWeight: 600,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "var(--forest)",
              animation: "pulse-dot 1.4s infinite",
            }}
          />
          Synced
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 3, height: 44 }}>
        {Array.from({ length: BAR_COUNT }, (_, index) => {
          const heightPx =
            8 + Math.sin(index * 0.5) * 12 + Math.cos(index * 0.9) * 8 + 18;
          const isActive = index >= 14 && index <= 19;
          return (
            <div
              key={index}
              style={{
                flex: 1,
                height: heightPx,
                background: isActive ? "var(--terracotta)" : "var(--hairline-strong)",
                borderRadius: 2,
                opacity: isActive ? 1 : 0.7,
              }}
            />
          );
        })}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
        <span className="mono" style={{ fontSize: 10, color: "var(--muted)" }}>
          00:00
        </span>
        <span
          className="mono"
          style={{ fontSize: 10, color: "var(--terracotta)", fontWeight: 600 }}
        >
          walk · 18 min
        </span>
        <span className="mono" style={{ fontSize: 10, color: "var(--muted)" }}>
          now
        </span>
      </div>
    </div>
  );
}
