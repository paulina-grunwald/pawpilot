import type { ReactNode } from "react";
import styles from "./Chip.module.css";

export type ChipVariant = "default" | "blue" | "forest" | "ochre" | "dark";

type ChipProps = {
  children: ReactNode;
  variant?: ChipVariant;
};

export function Chip({ children, variant = "default" }: ChipProps) {
  return <span className={`${styles.chip} ${styles[variant]}`}>{children}</span>;
}
