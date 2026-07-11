import { BaseIcon, type IconProps } from "./BaseIcon";

export function JournalIcon({ size = 24, strokeWidth = 1.8, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} strokeWidth={strokeWidth} {...rest}>
      <path d="M7 4h10a2 2 0 0 1 2 2v13a1 1 0 0 1-1 1H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z" />
      <path d="M9.5 4v16" />
      <path d="M12.5 9h4M12.5 12.5h4" />
    </BaseIcon>
  );
}
