import type { ButtonHTMLAttributes, ReactNode } from "react";

type SubmitButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "type"> & {
  isSubmitting?: boolean;
  isHydrating?: boolean;
  loadingLabel?: string;
  children: ReactNode;
};

export function SubmitButton({
  isSubmitting = false,
  isHydrating = false,
  loadingLabel = "Loading…",
  disabled,
  children,
  className,
  ...buttonProps
}: SubmitButtonProps) {
  const isUnavailable = Boolean(disabled) || isSubmitting;
  const isDisabled = isUnavailable || isHydrating;
  return (
    <button
      type="submit"
      disabled={isDisabled}
      aria-busy={isSubmitting || undefined}
      className={`focus-ring inline-flex w-full items-center justify-center rounded-full px-4 py-2.5 text-[14px] font-medium text-paper transition-opacity ${isDisabled ? "cursor-not-allowed" : ""} ${isUnavailable ? "opacity-60" : ""} ${className ?? ""}`.replace(/\s+/g, " ").trim()}
      style={{ background: "var(--ink)" }}
      {...buttonProps}
    >
      {isSubmitting ? (
        <>
          <span className="sr-only">{loadingLabel}</span>
          <span aria-hidden="true">{children}</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}
