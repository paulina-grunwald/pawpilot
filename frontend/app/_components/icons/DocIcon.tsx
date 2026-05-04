import { BaseIcon, type IconProps } from "./BaseIcon";

export function DocIcon({ size = 20, strokeWidth = 1.7, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} strokeWidth={strokeWidth} {...rest}>
      <path d="M7 3h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" />
      <path d="M14 3v5h5M9 13h6M9 17h4" />
    </BaseIcon>
  );
}
