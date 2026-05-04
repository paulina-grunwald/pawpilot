import { BaseIcon, type IconProps } from "./BaseIcon";

export function AlertIcon({ size = 16, strokeWidth = 2, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} strokeWidth={strokeWidth} {...rest}>
      <path d="M12 3l10 18H2L12 3z" />
      <path d="M12 10v5M12 18.5v.01" />
    </BaseIcon>
  );
}
