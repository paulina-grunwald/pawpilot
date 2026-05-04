"use client";

import { useEffect, useRef, useState } from "react";
import { AlertIcon } from "../icons";

const data = [62, 58, 60, 55, 50, 47, 42, 39, 35, 31, 28, 24];
const WIDTH = 240;
const HEIGHT = 56;
const PADDING = 4;

export function AlertCard() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setVisible(true);
      },
      { threshold: 0.3 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const maximum = Math.max(...data);
  const minimum = Math.min(...data);
  const points = data.map<[number, number]>((value, index) => {
    const x = PADDING + (index / (data.length - 1)) * (WIDTH - PADDING * 2);
    const y = PADDING + (1 - (value - minimum) / (maximum - minimum)) * (HEIGHT - PADDING * 2);
    return [x, y];
  });
  const path = points
    .map((point, index) => (index === 0 ? `M${point[0]},${point[1]}` : `L${point[0]},${point[1]}`))
    .join(" ");
  const lastPoint = points[points.length - 1];
  const area = `${path} L${lastPoint[0]},${HEIGHT} L${points[0][0]},${HEIGHT} Z`;

  return (
    <div
      ref={containerRef}
      className="w-80 rounded-[22px] border border-(--hairline-strong) bg-(--paper) p-[18px] shadow-[0_1px_0_color-mix(in_srgb,var(--ink)_2%,transparent)]"
    >
      <div className="mb-3 flex items-center gap-2">
        <span className="text-ochre inline-flex h-7 w-7 items-center justify-center rounded-lg bg-[color-mix(in_srgb,var(--ochre)_14%,transparent)]">
          <AlertIcon />
        </span>
        <div className="flex-1">
          <div className="mono text-muted text-[10.5px] tracking-[0.08em] uppercase">
            Heads up · 7:42 am
          </div>
          <div className="text-ink text-[13px] font-semibold">Haru · 6yr Aussie</div>
        </div>
        <span className="text-muted text-[11px]">•••</span>
      </div>

      <div className="text-ink mb-[14px] text-[17px] leading-[1.4] font-medium">
        Activity is down <span className="text-ochre font-bold">38%</span> vs. her 30-day baseline,
        three days running.
      </div>

      <div className="bg-surface mb-3 rounded-[14px] border border-(--hairline) px-[14px] py-3">
        <div className="mb-[6px] flex items-baseline justify-between">
          <span className="mono text-muted text-[10px] tracking-[0.08em] uppercase">
            Active mins / day
          </span>
          <span className="mono text-ochre text-[11px] font-semibold">↓ 38%</span>
        </div>
        <svg
          width={WIDTH}
          height={HEIGHT}
          className="block h-auto w-full"
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        >
          <defs>
            <linearGradient id="alert-card-spark-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--ochre)" stopOpacity="0.22" />
              <stop offset="100%" stopColor="var(--ochre)" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={area} fill="url(#alert-card-spark-fill)" />
          <path
            d={path}
            fill="none"
            stroke="var(--ochre)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{
              strokeDasharray: 600,
              strokeDashoffset: visible ? 0 : 600,
              transition: "stroke-dashoffset 1.4s cubic-bezier(.6,.1,.3,1)",
            }}
          />
          {visible && (
            <g
              style={{
                transformOrigin: `${lastPoint[0]}px ${lastPoint[1]}px`,
                animation: "pulse-dot 1.8s ease-in-out 1.4s infinite",
              }}
            >
              <circle cx={lastPoint[0]} cy={lastPoint[1]} r="3.5" fill="var(--ochre)" />
            </g>
          )}
        </svg>
      </div>

      <div className="text-muted mb-[14px] text-[13.5px] leading-[1.5]">
        For Vizslas her age, this often points to{" "}
        <span className="text-ink font-medium">
          tick-borne illness, joint pain, or low-grade GI discomfort
        </span>{" "}
        — not yet urgent, worth a closer look.
      </div>

      <div className="flex gap-2">
        <button className="bg-forest text-paper flex-1 rounded-[10px] border-none px-3 py-2.5 text-[13px] font-medium">
          Ask PawPilot
        </button>
        <button className="text-ink rounded-[10px] border border-(--hairline-strong) bg-transparent px-3 py-[10px] text-[13px] font-medium">
          Snooze
        </button>
      </div>
    </div>
  );
}
