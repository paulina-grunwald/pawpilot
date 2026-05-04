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
    <div className="flex flex-col gap-2 mt-[14px]">
      {messages.map((message, index) => {
        const shown = step > index;
        const isFinal = index === messages.length - 1;
        return (
          <div
            key={index}
            className="flex gap-2 items-start"
            style={{
              opacity: shown ? 1 : 0.15,
              transform: shown ? "translateY(0)" : "translateY(4px)",
              transition: "all 400ms ease",
            }}
          >
            <span
              className="mono text-[9px] px-[7px] py-[3px] rounded-full tracking-[0.06em] uppercase whitespace-nowrap mt-px"
              style={{
                background: isFinal ? "var(--ink)" : "transparent",
                color: isFinal ? "var(--paper)" : message.color,
                border: isFinal ? "none" : `1px solid ${message.color}`,
              }}
            >
              {message.who}
            </span>
            <span className="text-[12.5px] text-ink leading-[1.4]">
              {message.text}
            </span>
          </div>
        );
      })}
    </div>
  );
}
