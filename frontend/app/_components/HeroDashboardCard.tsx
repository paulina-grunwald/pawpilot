"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import { AlertIcon } from "./icons";

const ACTIVITY_MINUTES = [62, 58, 60, 55, 50, 47, 42, 39, 35, 31, 28, 24];
const CHART_WIDTH = 240;
const CHART_HEIGHT = 68;
const CHART_PADDING = 4;

const HARU_THUMB = "/img/sunset-dog.png";

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

  const max = Math.max(...ACTIVITY_MINUTES);
  const min = Math.min(...ACTIVITY_MINUTES);
  const points = ACTIVITY_MINUTES.map<[number, number]>((value, index) => [
    CHART_PADDING + (index / (ACTIVITY_MINUTES.length - 1)) * (CHART_WIDTH - CHART_PADDING * 2),
    CHART_PADDING + (1 - (value - min) / (max - min)) * (CHART_HEIGHT - CHART_PADDING * 2),
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
      style={{
        background: "var(--card)",
        borderRadius: 14,
        padding: 16,
        border: "1.5px solid var(--ink)",
        boxShadow: "8px 8px 0 0 var(--blue)",
        width: 280,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <span
          style={{
            position: "relative",
            width: 28,
            height: 28,
            borderRadius: "50%",
            overflow: "hidden",
            flexShrink: 0,
            border: "1px solid var(--hairline)",
          }}
        >
          <Image
            src={HARU_THUMB}
            alt=""
            fill
            sizes="28px"
            style={{ objectFit: "cover" }}
          />
        </span>
        <div>
          <div style={{ fontSize: 12, fontWeight: 600 }}>Haru</div>
          <div
            className="mono"
            style={{ fontSize: 9, color: "var(--muted-2)", letterSpacing: "0.06em" }}
          >
            AUSTRALIAN SHEPHERD · 6Y
          </div>
        </div>
        <span
          style={{
            marginLeft: "auto",
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
            fontSize: 10,
            color: "var(--warm)",
            fontWeight: 600,
          }}
        >
          <AlertIcon /> ALERT
        </span>
      </div>
      <div
        style={{
          padding: 12,
          marginBottom: 10,
          background: "color-mix(in srgb, var(--warm) 8%, transparent)",
          border: "1px solid color-mix(in srgb, var(--warm) 30%, transparent)",
          borderRadius: 8,
        }}
      >
        <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>
          Activity ↓ 38% · 3-day window
        </div>
        <div style={{ fontSize: 11, color: "var(--muted)", lineHeight: 1.5 }}>
          For Australian Shepherd her age, often points to tick-borne illness or low-grade joint
          pain.
        </div>
      </div>
      <div
        className="mono"
        style={{
          fontSize: 9,
          color: "var(--muted-2)",
          letterSpacing: "0.06em",
          marginBottom: 4,
        }}
      >
        ACTIVE MINS · LAST 12D
      </div>
      <svg
        width={CHART_WIDTH}
        height={CHART_HEIGHT}
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        style={{ width: "100%", display: "block" }}
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
