import { BaseIcon, type IconProps } from "./BaseIcon";

export function SignalIcon({ size = 18, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} {...rest}>
      <path d="M3 12c1.5-1.5 3.5-2.5 5-2.5" />
      <path d="M3 16c2.5-2.5 6-4 9-4" />
      <circle cx="13" cy="17" r="1.6" fill="currentColor" />
      <path d="M17 8l4-4M21 8l-4-4" />
    </BaseIcon>
  );
}
