import type { ReactNode } from "react";
import { CollarMini } from "./CollarMini";
import { AlertMini } from "./AlertMini";
import { DebateMini } from "./DebateMini";
import { MemoryMini } from "./MemoryMini";
import { BellIcon, BrainIcon, ScaleIcon, SignalIcon } from "./icons";

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
    <section id="why" style={{ paddingTop: 80, paddingBottom: 80, position: "relative" }}>
      <div className="container-x">
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            gap: 24,
            marginBottom: 48,
            flexWrap: "wrap",
          }}
        >
          <span
            className="mono"
            style={{
              fontSize: 11,
              color: "var(--muted)",
              letterSpacing: "0.16em",
              textTransform: "uppercase",
            }}
          >
            § 02 — Why PawPilot
          </span>
          <h2
            className="display"
            style={{
              fontSize: "clamp(32px, 4vw, 52px)",
              margin: 0,
              maxWidth: 760,
              color: "var(--ink)",
            }}
          >
            Four things a generic chatbot{" "}
            <span className="display-italic" style={{ color: "var(--blue)" }}>
              fundamentally can&apos;t do.
            </span>
          </h2>
        </div>

        <div
          className="diff-grid"
          style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 20 }}
        >
          {cards.map((card, index) => (
            <article
              key={index}
              style={{
                background: "var(--surface)",
                border: "1px solid var(--hairline)",
                borderRadius: 24,
                padding: 28,
                position: "relative",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  marginBottom: 16,
                }}
              >
                <span
                  className="mono"
                  style={{ fontSize: 11, color: "var(--muted)", letterSpacing: "0.12em" }}
                >
                  {card.eyebrow}
                </span>
                <span
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 10,
                    background: "var(--paper)",
                    border: "1px solid var(--hairline)",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: card.iconColor,
                  }}
                >
                  {card.icon}
                </span>
              </div>
              <h3
                className="display"
                style={{
                  fontSize: 26,
                  margin: "0 0 10px",
                  fontWeight: 500,
                  lineHeight: 1.15,
                  color: "var(--ink)",
                }}
              >
                {card.title}
              </h3>
              <p
                style={{
                  fontSize: 14.5,
                  color: "var(--muted)",
                  margin: 0,
                  lineHeight: 1.55,
                }}
              >
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
