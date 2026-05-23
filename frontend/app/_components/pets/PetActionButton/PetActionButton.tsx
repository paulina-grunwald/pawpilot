import type { ButtonHTMLAttributes, ReactNode } from "react";
import styles from "./PetActionButton.module.css";

type Variant = "default" | "primary" | "danger";

type PetActionButtonProps = {
  variant?: Variant;
  children: ReactNode;
} & ButtonHTMLAttributes<HTMLButtonElement>;

export function PetActionButton({
  variant = "default",
  children,
  type = "button",
  className,
  ...rest
}: PetActionButtonProps) {
  const classes = [styles.button, styles[variant], className].filter(Boolean).join(" ");
  return (
    <button type={type} className={classes} {...rest}>
      {children}
    </button>
  );
}
