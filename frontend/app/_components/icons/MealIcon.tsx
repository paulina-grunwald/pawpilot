import { BaseIcon, type IconProps } from "./BaseIcon";

export function MealIcon({ size = 20, strokeWidth = 1.8, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} strokeWidth={strokeWidth} {...rest}>
      <path d="M3 11h18" />
      <path d="M4.5 11a7.5 7.5 0 0 0 15 0" />
      <path d="M12 4.5c-2 0-3 1.2-3 2.6S10 11 12 11s3-1.5 3-3.9S14 4.5 12 4.5z" />
    </BaseIcon>
  );
}
