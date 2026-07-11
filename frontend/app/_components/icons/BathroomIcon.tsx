import { BaseIcon, type IconProps } from "./BaseIcon";

export function BathroomIcon({ size = 20, strokeWidth = 1.8, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} strokeWidth={strokeWidth} {...rest}>
      <path d="M12 3.5c0 0 6 6.2 6 10.1a6 6 0 0 1-12 0C6 9.7 12 3.5 12 3.5z" />
    </BaseIcon>
  );
}
