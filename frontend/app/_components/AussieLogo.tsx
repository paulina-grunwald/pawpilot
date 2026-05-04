import { Dog } from "lucide-react";
import type { ComponentProps } from "react";

type AussieLogoProps = Omit<ComponentProps<typeof Dog>, "size"> & {
  size?: number;
};

export function AussieLogo({ size = 28, color = "#FAF7F2", ...rest }: AussieLogoProps) {
  return (
    <Dog
      width={size}
      height={size}
      color={color}
      strokeWidth={1.6}
      aria-label="PawPilot"
      {...rest}
    />
  );
}
