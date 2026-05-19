import Image from "next/image";

type PawMarkProps = {
  size?: number;
  variant?: "badge" | "wordmark";
  className?: string;
};

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
        objectFit: "contain",
        flexShrink: 0,
      }}
    />
  );
}
