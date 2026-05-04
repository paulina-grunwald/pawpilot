import type { ReactNode } from "react";
import { CollarMini } from "../CollarMini";
import { AlertMini } from "../AlertMini";
import { DebateMini } from "../DebateMini";
import { MemoryMini } from "../MemoryMini";
import { BellIcon, BrainIcon, ScaleIcon, SignalIcon } from "../icons";

type Card = {
  eyebrow: string;
  title: string;
  body: string;
  icon: ReactNode;
  surface: ReactNode;
  iconColor: string;
};

const cards: Card[] = [
  {
    eyebrow: "01",
    title: "Speaks fluent Tractive.",
    body: "Pulls activity, sleep, and location from the collar your dog already wears. No new hardware, no new app to babysit.",
    icon: <SignalIcon />,
    surface: <CollarMini />,
    iconColor: "var(--blue)",
  },
  {
    eyebrow: "02",
    title: "Notices before you do.",
    body: "Builds a 30-day baseline per dog. Drifts of 15%+ get a gentle nudge — never a panic alarm. You hear about it Tuesday, not next month.",
    icon: <BellIcon />,
    surface: <AlertMini />,
    iconColor: "var(--ochre)",
  },
  {
    eyebrow: "03",
    title: "Two minds, no echo chamber.",
    body: "A Researcher proposes; a Skeptic challenges; a Synthesizer settles it. You get the conclusion and the receipts.",
    icon: <BrainIcon />,
    surface: <DebateMini />,
    iconColor: "var(--forest)",
  },
  {
    eyebrow: "04",
    title: "Remembers Haru's whole story.",
    body: "Vaccines from 2021. The chicken allergy from last spring. The hip thing the vet flagged. It's all context, every time you ask.",
    icon: <ScaleIcon />,
    surface: <MemoryMini />,
    iconColor: "var(--forest)",
  },
];

export function Differentiators() {
  return (
    <section id="why" className="pt-20 pb-20 relative">
      <div className="container-x">
        <div className="flex items-baseline gap-6 mb-12 flex-wrap">
          <span className="mono text-[11px] text-muted tracking-[0.16em] uppercase">
            § 02 — Why PawPilot
          </span>
          <h2
            className="display text-[clamp(32px,4vw,52px)] m-0 max-w-[760px] text-ink"
          >
            Four things a generic chatbot{" "}
            <span className="display-italic text-blue">
              fundamentally can&apos;t do.
            </span>
          </h2>
        </div>

        <div
          className="diff-grid grid gap-5"
          style={{ gridTemplateColumns: "repeat(2, 1fr)" }}
        >
          {cards.map((card, index) => (
            <article
              key={index}
              className="bg-surface border border-(--hairline) rounded-[24px] p-7 relative"
            >
              <div className="flex justify-between items-start mb-4">
                <span className="mono text-[11px] text-muted tracking-[0.12em]">
                  {card.eyebrow}
                </span>
                <span
                  className="w-8 h-8 rounded-[10px] bg-(--paper) border border-(--hairline) inline-flex items-center justify-center"
                  style={{ color: card.iconColor }}
                >
                  {card.icon}
                </span>
              </div>
              <h3
                className="display text-[26px] m-0 mb-[10px] font-medium leading-[1.15] text-ink"
              >
                {card.title}
              </h3>
              <p className="text-[14.5px] text-muted m-0 leading-[1.55]">
                {card.body}
              </p>
              {card.surface}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
