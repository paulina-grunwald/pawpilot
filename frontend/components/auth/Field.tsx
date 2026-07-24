import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from "react";

type FieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "id"> & {
  label: ReactNode;
  error?: string;
  helpText?: string;
};

export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, error, helpText, ...inputProps },
  ref,
) {
  const generatedId = useId();
  const inputId = inputProps.name ? `field-${inputProps.name}` : `field-${generatedId}`;
  const errorId = `${inputId}-error`;
  const helpId = `${inputId}-help`;
  const describedBy =
    [error ? errorId : null, helpText && !error ? helpId : null].filter(Boolean).join(" ") ||
    undefined;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={inputId} className="text-ink text-[13px] font-medium">
        {label}
      </label>
      <input
        ref={ref}
        id={inputId}
        aria-invalid={error ? "true" : undefined}
        aria-describedby={describedBy}
        className="focus-ring rounded-lg border px-3 py-2.5 text-[15px] transition-colors outline-none"
        style={{
          background: "var(--paper)",
          borderColor: error ? "var(--terracotta)" : "var(--hairline-strong)",
          color: "var(--ink)",
        }}
        {...inputProps}
      />
      {helpText && !error && (
        <p id={helpId} className="text-muted text-[12px]">
          {helpText}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className="text-[13px]" style={{ color: "var(--terracotta)" }}>
          {error}
        </p>
      )}
    </div>
  );
});
