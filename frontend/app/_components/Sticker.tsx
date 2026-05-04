import type { ReactNode } from "react";

type StickerProps = {
  children: ReactNode;
  color?: string;
  rotate?: number;
  top?: number | string;
  right?: number | string;
  bottom?: number | string;
  left?: number | string;
};

export function Sticker({
  children,
  color = "var(--blue)",
  rotate = -8,
  top,
  right,
  bottom,
  left,
}: StickerProps) {
  return (
    <div
      style={{
        position: "absolute",
        top,
        right,
        bottom,
        left,
        background: color,
        color: "#fff",
        fontFamily: "inherit",
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        padding: "6px 10px",
        borderRadius: 4,
        transform: `rotate(${rotate}deg)`,
        boxShadow: "0 4px 10px rgba(20,30,90,0.25)",
        whiteSpace: "nowrap",
        zIndex: 2,
      }}
    >
      {children}
    </div>
  );
}
