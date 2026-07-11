import { BaseIcon, type IconProps } from "./BaseIcon";

export function MoreIcon({ size = 20, strokeWidth = 2.2, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} strokeWidth={strokeWidth} {...rest}>
      <path d="M6 12h.01M12 12h.01M18 12h.01" />
    </BaseIcon>
  );
}
