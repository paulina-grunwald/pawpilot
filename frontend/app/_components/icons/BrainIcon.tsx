import { BaseIcon, type IconProps } from "./BaseIcon";

export function BrainIcon({ size = 18, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} {...rest}>
      <path d="M9 4a3 3 0 0 0-3 3v1a3 3 0 0 0-2 5 3 3 0 0 0 2 5v1a3 3 0 0 0 6 0V4a3 3 0 0 0-3 0z" />
      <path d="M15 4a3 3 0 0 1 3 3v1a3 3 0 0 1 2 5 3 3 0 0 1-2 5v1a3 3 0 0 1-6 0" />
    </BaseIcon>
  );
}
