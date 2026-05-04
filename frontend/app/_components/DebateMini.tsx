"use client";

import { useEffect, useState } from "react";

type Speaker = {
  who: string;
  color: string;
  text: string;
};

const messages: Speaker[] = [
  {
    who: "Researcher",
    color: "var(--forest)",
    text: "38% drop, 3-day window. Pattern fits early Lyme onset in the literature.",
  },
  {
    who: "Skeptic",
    color: "var(--terracotta)",
    text: "Or it's the heatwave. Phoenix hit 41°C Tue–Thu — most dogs slow down.",
  },
  {
    who: "Researcher",
    color: "var(--forest)",
    text: "Fair. Sleep duration is also up 22% though. Less common in heat-only cases.",
  },
  {
    who: "Synth",
    color: "var(--ink)",
    text: "Watch tonight. If activity stays low after sunset cool-down, vet visit Wed.",
  },
];

export function DebateMini() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(
      () => setStep((current) => (current + 1) % (messages.length + 1)),
      2200,
    );
    return () => clearInterval(timer);
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 14 }}>
      {messages.map((message, index) => {
        const shown = step > index;
        const isFinal = index === messages.length - 1;
        return (
          <div
            key={index}
            style={{
              opacity: shown ? 1 : 0.15,
              transform: shown ? "translateY(0)" : "translateY(4px)",
              transition: "all 400ms ease",
              display: "flex",
              gap: 8,
              alignItems: "flex-start",
            }}
          >
            <span
              className="mono"
              style={{
                fontSize: 9,
                padding: "3px 7px",
                borderRadius: 999,
                background: isFinal ? "var(--ink)" : "transparent",
                color: isFinal ? "var(--paper)" : message.color,
                border: isFinal ? "none" : `1px solid ${message.color}`,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                whiteSpace: "nowrap",
                marginTop: 1,
              }}
            >
              {message.who}
            </span>
            <span style={{ fontSize: 12.5, color: "var(--ink)", lineHeight: 1.4 }}>
              {message.text}
            </span>
          </div>
        );
      })}
    </div>
  );
}
