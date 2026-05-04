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
  unoptimized = true,
}: PolaroidProps) {
  return (
    <div
      style={{
        background: "var(--card)",
        padding: "12px 12px 18px",
        boxShadow:
          "0 14px 32px -14px rgba(20,20,15,0.34), 0 2px 6px rgba(20,20,15,0.08)",
        transform: `rotate(${rotate}deg)`,
        width,
        border: "1px solid rgba(0,0,0,0.04)",
        position: "relative",
        ...style,
      }}
    >
      <div
        aria-hidden
        style={{
          position: "absolute",
          top: -10,
          left: "50%",
          transform: "translateX(-50%) rotate(-3deg)",
          width: 70,
          height: 22,
          background: "rgba(255,240,180,0.7)",
          borderLeft: "1px dashed rgba(0,0,0,0.06)",
          borderRight: "1px dashed rgba(0,0,0,0.06)",
        }}
      />
      <div
        style={{
          width: "100%",
          aspectRatio: "1 / 1",
          overflow: "hidden",
          background: "var(--surface-2)",
          position: "relative",
        }}
      >
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
        <div
          className="hand"
          style={{
            textAlign: "center",
            marginTop: 10,
            fontSize: 22,
            color: "var(--ink)",
            lineHeight: 1,
          }}
        >
          {caption}
        </div>
      )}
      {sticker}
    </div>
  );
}
