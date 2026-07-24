"use client";

import { useEffect, useState } from "react";
import { PawMark } from "../PawMark";

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
    <div className="max-w-[560px] rounded-[22px] border border-(--hairline-strong) bg-(--paper) p-[22px]">
      <div className="text-ink mr-auto mb-[14px] max-w-[80%] rounded-[14px_14px_14px_4px] bg-(--surface-2) px-4 py-3 text-[15px] leading-[1.5]">
        <span key={queryIndex} className="inline-block" style={{ animation: "fade-in 400ms ease" }}>
          {queries[queryIndex]}
        </span>
      </div>

      <div className="mb-2 flex items-center gap-2">
        <PawMark size={28} />
        <span className="mono text-muted text-[10.5px] tracking-[0.06em] uppercase">
          PawPilot · low urgency
        </span>
      </div>

      <div className="bg-surface text-ink rounded-[4px_14px_14px_14px] px-[18px] py-[14px] text-[15px] leading-[1.55]">
        <p className="m-0 mb-[10px]">
          <strong>One grape is unlikely to harm a 22 kg dog</strong>, but grape toxicity has no
          clean dose-response in the literature — some dogs react to very little
          <sup className="text-blue text-[10px] font-semibold">[1]</sup>.
        </p>
        <p className="text-muted m-0 mb-[14px]">
          Watch Haru for vomiting or lethargy over the next 6–12 hours. Given her healthy kidney
          panel from March, the risk is low, not zero
          <sup className="text-blue text-[10px] font-semibold">[2]</sup>.
        </p>

        <div className="flex flex-col gap-[6px] border-t border-(--hairline) pt-3">
          {citations.map((citation) => (
            <div key={citation.number} className="flex items-baseline gap-2 text-[12px]">
              <sup className="text-blue text-[10px] font-bold">[{citation.number}]</sup>
              <span className="text-ink font-medium">{citation.source}</span>
              <span className="mono text-muted text-[10.5px]">{citation.fragment}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
