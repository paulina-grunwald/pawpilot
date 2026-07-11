import { BaseIcon, type IconProps } from "./BaseIcon";

export function CloseIcon({ size = 24, strokeWidth = 2, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} strokeWidth={strokeWidth} {...rest}>
      <path d="M6 6l12 12M18 6L6 18" />
    </BaseIcon>
  );
}
