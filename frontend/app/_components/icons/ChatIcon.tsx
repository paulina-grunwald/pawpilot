import { BaseIcon, type IconProps } from "./BaseIcon";

export function ChatIcon({ size = 20, strokeWidth = 1.7, ...rest }: IconProps) {
  return (
    <BaseIcon size={size} strokeWidth={strokeWidth} {...rest}>
      <path d="M5 5h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-8l-5 4v-4H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z" />
    </BaseIcon>
  );
}
