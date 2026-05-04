"use client";

import { useEffect, useState } from "react";
import { PawMark } from "./PawMark";

const queries = [
  "Did Haru just eat a grape? She grabbed one off the counter.",
  "Is this rash on her belly something to worry about?",
  "Why is she limping after our morning walk?",
];

const citations = [
  {
    number: 1,
    source: "ACVIM Toxicology Guidelines, 2023",
    fragment: "§ 4.2 Vitis vinifera",
  },
  {
    number: 2,
    source: "Haru's bloodwork",
    fragment: "Mar 14, 2024 · BUN/Creat normal",
  },
];

export function ChatBubble() {
  const [queryIndex, setQueryIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(
      () => setQueryIndex((current) => (current + 1) % queries.length),
      4500,
    );
    return () => clearInterval(timer);
  }, []);

  return (
    <div
      style={{
        background: "var(--paper)",
        border: "1px solid var(--hairline-strong)",
        borderRadius: 22,
        padding: 22,
        maxWidth: 560,
      }}
    >
      <div
        style={{
          background: "var(--surface-2)",
          borderRadius: "14px 14px 14px 4px",
          padding: "12px 16px",
          marginBottom: 14,
          marginRight: "auto",
          maxWidth: "80%",
          fontSize: 15,
          color: "var(--ink)",
          lineHeight: 1.5,
        }}
      >
        <span
          key={queryIndex}
          style={{ display: "inline-block", animation: "fade-in 400ms ease" }}
        >
          {queries[queryIndex]}
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <PawMark size={28} />
        <span
          className="mono"
          style={{
            fontSize: 10.5,
            color: "var(--muted)",
            letterSpacing: "0.06em",
            textTransform: "uppercase",
          }}
        >
          PawPilot · low urgency
        </span>
      </div>

      <div
        style={{
          background: "var(--surface)",
          borderRadius: "4px 14px 14px 14px",
          padding: "14px 18px",
          fontSize: 15,
          color: "var(--ink)",
          lineHeight: 1.55,
        }}
      >
        <p style={{ margin: "0 0 10px" }}>
          <strong>One grape is unlikely to harm a 22 kg dog</strong>, but grape toxicity has no
          clean dose-response in the literature — some dogs react to very little
          <sup style={{ fontSize: 10, color: "var(--blue)", fontWeight: 600 }}>[1]</sup>.
        </p>
        <p style={{ margin: "0 0 14px", color: "var(--muted)" }}>
          Watch Haru for vomiting or lethargy over the next 6–12 hours. Given her healthy kidney
          panel from March, the risk is low, not zero
          <sup style={{ fontSize: 10, color: "var(--blue)", fontWeight: 600 }}>[2]</sup>.
        </p>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 6,
            paddingTop: 12,
            borderTop: "1px solid var(--hairline)",
          }}
        >
          {citations.map((citation) => (
            <div
              key={citation.number}
              style={{ display: "flex", alignItems: "baseline", gap: 8, fontSize: 12 }}
            >
              <sup style={{ color: "var(--blue)", fontWeight: 700, fontSize: 10 }}>
                [{citation.number}]
              </sup>
              <span style={{ color: "var(--ink)", fontWeight: 500 }}>
                {citation.source}
              </span>
              <span className="mono" style={{ color: "var(--muted)", fontSize: 10.5 }}>
                {citation.fragment}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
