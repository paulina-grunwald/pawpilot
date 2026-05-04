import { AlertCard } from "./AlertCard";

export function PhoneMock() {
  return (
    <div
      style={{
        position: "relative",
        width: 360,
        height: 640,
        borderRadius: 48,
        background: "var(--ink)",
        padding: 10,
        boxShadow: "0 30px 60px -20px rgba(31,27,22,0.35), 0 0 0 1px rgba(31,27,22,0.06)",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 18,
          left: "50%",
          transform: "translateX(-50%)",
          width: 100,
          height: 26,
          borderRadius: 14,
          background: "#000",
          zIndex: 2,
        }}
      />
      <div
        style={{
          width: "100%",
          height: "100%",
          borderRadius: 40,
          background: "linear-gradient(180deg, #F2EDE4 0%, #FAF7F2 30%)",
          position: "relative",
          overflow: "hidden",
          padding: "54px 18px 24px",
        }}
      >
        <div
          className="mono"
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 11,
            color: "var(--ink)",
            marginBottom: 24,
            padding: "0 12px",
          }}
        >
          <span>9:41</span>
          <span style={{ display: "flex", gap: 4, alignItems: "center" }}>
            <span>·•••</span>
            <span>100%</span>
          </span>
        </div>

        <div style={{ padding: "0 6px 18px" }}>
          <div
            className="mono"
            style={{
              fontSize: 10,
              color: "var(--muted)",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              marginBottom: 4,
            }}
          >
            Tuesday
          </div>
          <div
            className="display"
            style={{ fontSize: 22, fontWeight: 500, color: "var(--ink)", lineHeight: 1.15 }}
          >
            Morning.{" "}
            <span className="display-italic" style={{ color: "var(--forest)" }}>
              Haru&apos;s a little off.
            </span>
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "center" }}>
          <div style={{ transform: "scale(0.96)", transformOrigin: "top center" }}>
            <AlertCard />
          </div>
        </div>
      </div>
    </div>
  );
}
