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
    <section id="why" className="relative pt-20 pb-20">
      <div className="container-x">
        <div className="mb-12 flex flex-wrap items-baseline gap-6">
          <span className="mono text-muted text-[11px] tracking-[0.16em] uppercase">
            § 02 — Why PawPilot
          </span>
          <h2 className="display text-ink m-0 max-w-[760px] text-[clamp(32px,4vw,52px)]">
            Four things a generic chatbot{" "}
            <span className="display-italic text-blue">fundamentally can&apos;t do.</span>
          </h2>
        </div>

        <div className="diff-grid grid gap-5" style={{ gridTemplateColumns: "repeat(2, 1fr)" }}>
          {cards.map((card, index) => (
            <article
              key={index}
              className="bg-surface relative rounded-[24px] border border-(--hairline) p-7"
            >
              <div className="mb-4 flex items-start justify-between">
                <span className="mono text-muted text-[11px] tracking-[0.12em]">
                  {card.eyebrow}
                </span>
                <span
                  className="inline-flex h-8 w-8 items-center justify-center rounded-[10px] border border-(--hairline) bg-(--paper)"
                  style={{ color: card.iconColor }}
                >
                  {card.icon}
                </span>
              </div>
              <h3 className="display text-ink m-0 mb-[10px] text-[26px] leading-[1.15] font-medium">
                {card.title}
              </h3>
              <p className="text-muted m-0 text-[14.5px] leading-[1.55]">{card.body}</p>
              {card.surface}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
