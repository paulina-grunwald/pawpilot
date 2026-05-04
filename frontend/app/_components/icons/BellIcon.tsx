import { BaseIcon, type IconProps } from "./BaseIcon";

export function BellIcon({ size = 18, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} {...rest}>
      <path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2H4.5L6 16z" />
      <path d="M10 20a2 2 0 0 0 4 0" />
    </BaseIcon>
  );
}
