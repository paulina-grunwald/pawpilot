import { BaseIcon, type IconProps } from "./BaseIcon";

export function MoodIcon({ size = 20, strokeWidth = 1.8, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} strokeWidth={strokeWidth} {...rest}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M8.5 14a4 4 0 0 0 7 0" />
      <path d="M9 9.75h.01M15 9.75h.01" />
    </BaseIcon>
  );
}
