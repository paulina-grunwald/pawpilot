import { BaseIcon, type IconProps } from "./BaseIcon";

export function ArrowRightIcon({ size = 16, strokeWidth = 2, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} strokeWidth={strokeWidth} {...rest}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </BaseIcon>
  );
}
