import { BaseIcon, type IconProps } from "./BaseIcon";

export function ScaleIcon({ size = 18, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} {...rest}>
      <path d="M12 4v16M4 8h16" />
      <path d="M4 8l-2 5a4 4 0 0 0 8 0L8 8M16 8l-2 5a4 4 0 0 0 8 0l-2-5" />
    </BaseIcon>
  );
}
