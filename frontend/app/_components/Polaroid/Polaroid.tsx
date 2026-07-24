import Image from "next/image";
import type { CSSProperties, ReactNode } from "react";

type PolaroidProps = {
  src: string;
  alt?: string;
  caption?: string;
  rotate?: number;
  width?: number;
  objectPosition?: string;
  sticker?: ReactNode;
  style?: CSSProperties;
  unoptimized?: boolean;
};

export function Polaroid({
  src,
  alt = "",
  caption,
  rotate = -3,
  width = 220,
  objectPosition = "center",
  sticker,
  style,
  unoptimized = false,
}: PolaroidProps) {
  return (
    <div
      className="relative border border-[color-mix(in_srgb,var(--ink)_4%,transparent)] bg-(--card)"
      style={{
        padding: "12px 12px 18px",
        boxShadow:
          "0 14px 32px -14px color-mix(in srgb, var(--ink) 34%, transparent), 0 2px 6px color-mix(in srgb, var(--ink) 8%, transparent)",
        transform: `rotate(${rotate}deg)`,
        width,
        ...style,
      }}
    >
      <div
        aria-hidden
        className="absolute left-1/2 h-[22px] w-[70px] -translate-x-1/2 border-r border-l border-dashed border-[color-mix(in_srgb,var(--ink)_6%,transparent)]"
        style={{
          top: -10,
          transform: "translateX(-50%) rotate(-3deg)",
          background: "color-mix(in srgb, var(--tape) 70%, transparent)",
        }}
      />
      <div className="relative aspect-square w-full overflow-hidden bg-(--surface-2)">
        <Image
          src={src}
          alt={alt}
          fill
          sizes={`${width}px`}
          style={{
            objectFit: "cover",
            objectPosition,
            display: "block",
            filter: "contrast(1.02) saturate(0.95)",
          }}
          unoptimized={unoptimized}
        />
      </div>
      {caption && (
        <div className="hand text-ink mt-[10px] text-center text-[22px] leading-none">
          {caption}
        </div>
      )}
      {sticker}
    </div>
  );
}
