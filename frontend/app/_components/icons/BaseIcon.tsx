import type { ReactNode, SVGProps } from "react";

export type BaseIconProps = Omit<SVGProps<SVGSVGElement>, "width" | "height"> & {
  size?: number;
  color?: string;
  strokeWidth?: number;
  viewBox?: string;
  children: ReactNode;
};

export function BaseIcon({
  size = 24,
  color = "currentColor",
  strokeWidth = 1.8,
  viewBox = "0 0 24 24",
  children,
  ...rest
}: BaseIconProps) {
  return (
    <svg
      viewBox={viewBox}
      width={size}
      height={size}
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  );
}

export type IconProps = Omit<BaseIconProps, "children" | "viewBox">;
