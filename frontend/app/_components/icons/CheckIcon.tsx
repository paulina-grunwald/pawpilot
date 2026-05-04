import { BaseIcon, type IconProps } from "./BaseIcon";

export function CheckIcon({ size = 14, strokeWidth = 2.4, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} strokeWidth={strokeWidth} {...rest}>
      <path d="M4 12l5 5L20 6" />
    </BaseIcon>
  );
}
