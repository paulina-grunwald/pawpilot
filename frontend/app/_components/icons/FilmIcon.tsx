import { BaseIcon, type IconProps } from "./BaseIcon";

export function FilmIcon({ size = 20, strokeWidth = 1.7, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} strokeWidth={strokeWidth} {...rest}>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 9h18M3 15h18M8 4v16M16 4v16" />
    </BaseIcon>
  );
}
