import type { ReactElement } from "react";
import type { EntryType } from "@/lib/journal.constants";

type EntryTypeIconProps = {
  type: EntryType;
  size?: number;
};

function stroke(pathData: string, key: string): ReactElement {
  return (
    <path
      key={key}
      d={pathData}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  );
}

function dot(centerX: number, centerY: number, key: string): ReactElement {
  return <circle key={key} cx={centerX} cy={centerY} r={0.9} fill="currentColor" />;
}

const ICON_SHAPES: Record<EntryType, ReactElement[]> = {
  meal: [
    stroke("M2.5 9h15", "bowl"),
    stroke("M4.5 9a5.5 5 0 0 0 11 0", "food"),
    stroke("M10 3.5v2", "steam"),
  ],
  bathroom: [stroke("M10 3c3 3.8 4.5 6 4.5 8a4.5 4.5 0 0 1-9 0c0-2 1.5-4.2 4.5-8z", "drop")],
  symptom: [stroke("M2.5 11h4l1.6-4 2.8 8 1.6-4h4.5", "pulse")],
  mood: [
    <circle key="face" cx={10} cy={10} r={7} fill="none" stroke="currentColor" strokeWidth={1.6} />,
    stroke("M7 11.5a4 3 0 0 0 6 0", "smile"),
    dot(7.6, 8.4, "eyeLeft"),
    dot(12.4, 8.4, "eyeRight"),
  ],
  medication: [
    <rect
      key="pill"
      x={3.5}
      y={7.5}
      width={13}
      height={5}
      rx={2.5}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
    />,
    stroke("M10 7.5v5", "split"),
  ],
  weight: [
    stroke("M4 15a6 6 0 0 1 12 0", "arc"),
    stroke("M4 15h12", "base"),
    stroke("M10 15l2.6-3.6", "needle"),
  ],
  vet_visit: [
    stroke("M10 3l6 2.2v4.8c0 4-3 6-6 7-3-1-6-3-6-7V5.2z", "shield"),
    stroke("M10 7v5", "cross-v"),
    stroke("M7.5 9.5h5", "cross-h"),
  ],
  free_note: [
    <rect
      key="page"
      x={4}
      y={3.5}
      width={12}
      height={13}
      rx={2.2}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
    />,
    stroke("M7 8h6", "line-1"),
    stroke("M7 11h6", "line-2"),
    stroke("M7 14h3", "line-3"),
  ],
};

export function EntryTypeIcon({ type, size = 16 }: EntryTypeIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      role="presentation"
      aria-hidden="true"
      style={{ display: "block" }}
    >
      {ICON_SHAPES[type]}
    </svg>
  );
}

export function SearchIcon({ size = 18 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      role="presentation"
      aria-hidden="true"
      style={{ display: "block" }}
    >
      <circle cx={9} cy={9} r={5.2} fill="none" stroke="currentColor" strokeWidth={1.6} />
      <path
        d="M12.8 12.8L17 17"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.6}
        strokeLinecap="round"
      />
    </svg>
  );
}
