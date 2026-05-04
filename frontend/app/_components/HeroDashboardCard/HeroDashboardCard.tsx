"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import { AlertIcon } from "../icons";

const ACTIVITY_MINUTES = [62, 58, 60, 55, 50, 47, 42, 39, 35, 31, 28, 24];
const CHART_WIDTH = 240;
const CHART_HEIGHT = 68;
const CHART_PADDING = 4;

const HARU_THUMB = "/img/sunset-dog.webp";

export function HeroDashboardCard() {
  const cardRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!cardRef.current) return;
    const node = cardRef.current;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setVisible(true);
      },
      { threshold: 0.2 }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const maximum = Math.max(...ACTIVITY_MINUTES);
  const minimum = Math.min(...ACTIVITY_MINUTES);
  const points = ACTIVITY_MINUTES.map<[number, number]>((value, index) => [
    CHART_PADDING + (index / (ACTIVITY_MINUTES.length - 1)) * (CHART_WIDTH - CHART_PADDING * 2),
    CHART_PADDING +
      (1 - (value - minimum) / (maximum - minimum)) * (CHART_HEIGHT - CHART_PADDING * 2),
  ]);
  const path = points
    .map((point, index) => `${index ? "L" : "M"}${point[0]},${point[1]}`)
    .join(" ");
  const lastPoint = points[points.length - 1];
  const firstPoint = points[0];
  const area = `${path} L${lastPoint[0]},${CHART_HEIGHT} L${firstPoint[0]},${CHART_HEIGHT} Z`;

  return (
    <div
      ref={cardRef}
      className="bg-(--card) rounded-[14px] p-4 border-[1.5px] border-ink shadow-[8px_8px_0_0_var(--blue)] w-[280px]"
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="relative w-7 h-7 rounded-full overflow-hidden shrink-0 border border-(--hairline)">
          <Image
            src={HARU_THUMB}
            alt=""
            fill
            sizes="28px"
            style={{ objectFit: "cover" }}
          />
        </span>
        <div>
          <div className="text-[12px] font-semibold">Haru</div>
          <div className="mono text-[9px] text-(--muted-2) tracking-[0.06em]">
            AUSTRALIAN SHEPHERD · 6Y
          </div>
        </div>
        <span className="ml-auto inline-flex items-center gap-1 text-[10px] text-(--warm) font-semibold">
          <AlertIcon /> ALERT
        </span>
      </div>
      <div className="p-3 mb-[10px] bg-[color-mix(in_srgb,var(--warm)_8%,transparent)] border border-[color-mix(in_srgb,var(--warm)_30%,transparent)] rounded-lg">
        <div className="text-[12px] font-semibold mb-[2px]">
          Activity ↓ 38% · 3-day window
        </div>
        <div className="text-[11px] text-muted leading-[1.5]">
          For Australian Shepherd her age, often points to tick-borne illness or low-grade joint
          pain.
        </div>
      </div>
      <div className="mono text-[9px] text-(--muted-2) tracking-[0.06em] mb-1">
        ACTIVE MINS · LAST 12D
      </div>
      <svg
        width={CHART_WIDTH}
        height={CHART_HEIGHT}
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        className="w-full block"
        aria-hidden
      >
        <defs>
          <linearGradient id="hero-spark-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--warm)" stopOpacity="0.25" />
            <stop offset="100%" stopColor="var(--warm)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={area} fill="url(#hero-spark-fill)" />
        <path
          d={path}
          fill="none"
          stroke="var(--warm)"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{
            strokeDasharray: 600,
            strokeDashoffset: visible ? 0 : 600,
            transition: "stroke-dashoffset 1.4s ease",
          }}
        />
        {visible && (
          <circle
            cx={lastPoint[0]}
            cy={lastPoint[1]}
            r="3.5"
            fill="var(--warm)"
            style={{ animation: "pulse-dot 1.6s 1.4s infinite" }}
          />
        )}
      </svg>
    </div>
  );
}
