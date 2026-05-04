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
      className="absolute text-paper text-[11px] font-bold tracking-[0.08em] uppercase px-[10px] py-[6px] rounded-[4px] whitespace-nowrap z-[2] shadow-[0_4px_10px_color-mix(in_srgb,var(--blue-deep)_25%,transparent)]"
      style={{
        top,
        right,
        bottom,
        left,
        background: color,
        transform: `rotate(${rotate}deg)`,
      }}
    >
      {children}
    </div>
  );
}
