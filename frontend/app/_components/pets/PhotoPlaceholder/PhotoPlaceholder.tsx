import styles from "./PhotoPlaceholder.module.css";

type PhotoPlaceholderProps = {
  label?: string;
  radius?: number;
  width?: number | string;
  height?: number | string;
};

export function PhotoPlaceholder({
  label = "dog photo",
  radius = 12,
  width = "100%",
  height = "100%",
}: PhotoPlaceholderProps) {
  return (
    <div
      aria-hidden
      className={styles.placeholder}
      style={{ width, height, borderRadius: radius }}
    >
      <span className={`${styles.label} mono`}>{label}</span>
    </div>
  );
}
