import type { ButtonHTMLAttributes, ReactNode } from "react";
import styles from "./PetPickerButton.module.css";

type Variant = "default" | "primary" | "danger";

type PetPickerButtonProps = {
  variant?: Variant;
  children: ReactNode;
} & ButtonHTMLAttributes<HTMLButtonElement>;

export function PetPickerButton({
  variant = "default",
  children,
  type = "button",
  className,
  ...rest
}: PetPickerButtonProps) {
  const classes = [styles.button, styles[variant], className].filter(Boolean).join(" ");
  return (
    <button type={type} className={classes} {...rest}>
      {children}
    </button>
  );
}
