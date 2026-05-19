import Image from "next/image";

type PawMarkProps = {
  size?: number;
  variant?: "badge" | "wordmark";
  className?: string;
};

// Intrinsic aspect ratios of the source PNGs — passing matching width/height
// to next/image keeps the layout-shift contract correct and silences the
// "modified one dimension via CSS but not the other" runtime warning.
const SOURCES: Record<
  NonNullable<PawMarkProps["variant"]>,
  { src: string; intrinsicWidth: number; intrinsicHeight: number }
> = {
  badge: { src: "/assets/pawdoc-badge-v3.png", intrinsicWidth: 548, intrinsicHeight: 568 },
  wordmark: { src: "/assets/pawdoc-logo-v3.png", intrinsicWidth: 683, intrinsicHeight: 880 },
};

export function PawMark({ size = 56, variant = "badge", className }: PawMarkProps) {
  const { src, intrinsicWidth, intrinsicHeight } = SOURCES[variant];
  const width = Math.round((size * intrinsicWidth) / intrinsicHeight);
  return (
    <Image
      src={src}
      alt=""
      width={width}
      height={size}
      priority
      className={className}
      style={{
        display: "block",
        height: size,
        width: "auto",
        objectFit: "contain",
        flexShrink: 0,
      }}
    />
  );
}
