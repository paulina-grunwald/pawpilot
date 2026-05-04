import { BaseIcon, type IconProps } from "./BaseIcon";

export function CamIcon({ size = 20, strokeWidth = 1.7, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} strokeWidth={strokeWidth} {...rest}>
      <rect x="3" y="6.5" width="18" height="13" rx="2.5" />
      <circle cx="12" cy="13" r="3.5" />
      <path d="M8 6.5l1.5-2h5L16 6.5" />
    </BaseIcon>
  );
}
