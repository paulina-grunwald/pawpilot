"use client";

import { useEffect, useRef, useState } from "react";
import { AlertIcon } from "./icons";

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
    const y =
      PADDING +
      (1 - (value - minimum) / (maximum - minimum)) * (HEIGHT - PADDING * 2);
    return [x, y];
  });
  const path = points
    .map((point, index) =>
      index === 0 ? `M${point[0]},${point[1]}` : `L${point[0]},${point[1]}`,
    )
    .join(" ");
  const lastPoint = points[points.length - 1];
  const area = `${path} L${lastPoint[0]},${HEIGHT} L${points[0][0]},${HEIGHT} Z`;

  return (
    <div
      ref={containerRef}
      style={{
        background: "var(--paper)",
        border: "1px solid var(--hairline-strong)",
        borderRadius: 22,
        padding: 18,
        width: 320,
        boxShadow: "0 1px 0 rgba(0,0,0,0.02)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <span
          style={{
            width: 28,
            height: 28,
            borderRadius: 8,
            background: "rgba(200,132,30,0.14)",
            color: "var(--ochre)",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <AlertIcon />
        </span>
        <div style={{ flex: 1 }}>
          <div
            className="mono"
            style={{
              fontSize: 10.5,
              color: "var(--muted)",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Heads up · 7:42 am
          </div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--ink)" }}>
            Haru · 6yr Aussie
          </div>
        </div>
        <span style={{ fontSize: 11, color: "var(--muted)" }}>•••</span>
      </div>

      <div
        style={{
          fontSize: 17,
          lineHeight: 1.4,
          color: "var(--ink)",
          marginBottom: 14,
          fontWeight: 500,
        }}
      >
        Activity is down <span style={{ color: "var(--ochre)", fontWeight: 700 }}>38%</span> vs. her
        30-day baseline, three days running.
      </div>

      <div
        style={{
          background: "var(--surface)",
          borderRadius: 14,
          padding: "12px 14px",
          marginBottom: 12,
          border: "1px solid var(--hairline)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: 6,
          }}
        >
          <span
            className="mono"
            style={{
              fontSize: 10,
              color: "var(--muted)",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Active mins / day
          </span>
          <span className="mono" style={{ fontSize: 11, color: "var(--ochre)", fontWeight: 600 }}>
            ↓ 38%
          </span>
        </div>
        <svg
          width={WIDTH}
          height={HEIGHT}
          style={{ display: "block", width: "100%", height: "auto" }}
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        >
          <defs>
            <linearGradient id="sparkfill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--ochre)" stopOpacity="0.22" />
              <stop offset="100%" stopColor="var(--ochre)" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={area} fill="url(#sparkfill)" />
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
              <circle
                cx={lastPoint[0]}
                cy={lastPoint[1]}
                r="3.5"
                fill="var(--ochre)"
              />
            </g>
          )}
        </svg>
      </div>

      <div
        style={{
          fontSize: 13.5,
          color: "var(--muted)",
          lineHeight: 1.5,
          marginBottom: 14,
        }}
      >
        For Vizslas her age, this often points to{" "}
        <span style={{ color: "var(--ink)", fontWeight: 500 }}>
          tick-borne illness, joint pain, or low-grade GI discomfort
        </span>{" "}
        — not yet urgent, worth a closer look.
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <button
          style={{
            flex: 1,
            background: "var(--forest)",
            color: "var(--paper)",
            border: "none",
            padding: "10px 12px",
            borderRadius: 10,
            fontSize: 13,
            fontWeight: 500,
          }}
        >
          Ask PawPilot
        </button>
        <button
          style={{
            background: "transparent",
            color: "var(--ink)",
            border: "1px solid var(--hairline-strong)",
            padding: "10px 12px",
            borderRadius: 10,
            fontSize: 13,
            fontWeight: 500,
          }}
        >
          Snooze
        </button>
      </div>
    </div>
  );
}
