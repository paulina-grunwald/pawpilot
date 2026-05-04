import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

export const ArrowRightIcon = (props: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    width="16"
    height="16"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
);

export const SignalIcon = (props: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    width="18"
    height="18"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    {...props}
  >
    <path d="M3 12c1.5-1.5 3.5-2.5 5-2.5" />
    <path d="M3 16c2.5-2.5 6-4 9-4" />
    <circle cx="13" cy="17" r="1.6" fill="currentColor" />
    <path d="M17 8l4-4M21 8l-4-4" />
  </svg>
);

export const BellIcon = (props: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    width="18"
    height="18"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2H4.5L6 16z" />
    <path d="M10 20a2 2 0 0 0 4 0" />
  </svg>
);

export const ScaleIcon = (props: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    width="18"
    height="18"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M12 4v16M4 8h16" />
    <path d="M4 8l-2 5a4 4 0 0 0 8 0L8 8M16 8l-2 5a4 4 0 0 0 8 0l-2-5" />
  </svg>
);

export const BrainIcon = (props: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    width="18"
    height="18"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M9 4a3 3 0 0 0-3 3v1a3 3 0 0 0-2 5 3 3 0 0 0 2 5v1a3 3 0 0 0 6 0V4a3 3 0 0 0-3 0z" />
    <path d="M15 4a3 3 0 0 1 3 3v1a3 3 0 0 1 2 5 3 3 0 0 1-2 5v1a3 3 0 0 1-6 0" />
  </svg>
);

export const CamIcon = (props: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    width="20"
    height="20"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.7"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <rect x="3" y="6.5" width="18" height="13" rx="2.5" />
    <circle cx="12" cy="13" r="3.5" />
    <path d="M8 6.5l1.5-2h5L16 6.5" />
  </svg>
);

export const FilmIcon = (props: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    width="20"
    height="20"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.7"
    strokeLinecap="round"
    {...props}
  >
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <path d="M3 9h18M3 15h18M8 4v16M16 4v16" />
  </svg>
);

export const DocIcon = (props: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    width="20"
    height="20"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.7"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M7 3h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" />
    <path d="M14 3v5h5M9 13h6M9 17h4" />
  </svg>
);

export const ChatIcon = (props: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    width="20"
    height="20"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.7"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M5 5h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-8l-5 4v-4H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z" />
  </svg>
);

export const CheckIcon = (props: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    width="14"
    height="14"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.4"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M4 12l5 5L20 6" />
  </svg>
);

export const AlertIcon = (props: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    width="16"
    height="16"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M12 3l10 18H2L12 3z" />
    <path d="M12 10v5M12 18.5v.01" />
  </svg>
);
