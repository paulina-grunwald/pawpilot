import Image from "next/image";

type PawMarkProps = {
  size?: number;
  variant?: "badge" | "wordmark";
  className?: string;
};

const SOURCES: Record<NonNullable<PawMarkProps["variant"]>, string> = {
  badge: "/assets/pawdoc-logo.png",
  wordmark: "/assets/pawdoc-logo-v2.png",
};

export function PawMark({ size = 56, variant = "badge", className }: PawMarkProps) {
  const source = SOURCES[variant];
  return (
    <Image
      src={source}
      alt=""
      width={size}
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
