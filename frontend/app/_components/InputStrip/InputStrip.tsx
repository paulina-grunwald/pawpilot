import type { ComponentType } from "react";
import { ChatBubble } from "../ChatBubble";
import { CamIcon, ChatIcon, DocIcon, FilmIcon } from "../icons";
import type { IconProps } from "../icons";

type Tile = {
  Icon: ComponentType<IconProps>;
  label: string;
  subtitle: string;
  iconColor: string;
};

const tiles: Tile[] = [
  {
    Icon: CamIcon,
    label: "A photo",
    subtitle: "rash, lump, swollen paw",
    iconColor: "var(--blue)",
  },
  {
    Icon: FilmIcon,
    label: "Ten seconds of video",
    subtitle: "gait, limp, weird breathing",
    iconColor: "var(--forest)",
  },
  {
    Icon: DocIcon,
    label: "A bloodwork PDF",
    subtitle: "the vet's panel from last month",
    iconColor: "var(--ochre)",
  },
  {
    Icon: ChatIcon,
    label: "Just text",
    subtitle: '"did Haru just eat a grape?"',
    iconColor: "var(--ink)",
  },
];

export function InputStrip() {
  return (
    <section className="pt-24 pb-24">
      <div className="container-x">
        <div
          className="mm-grid grid gap-20 items-center"
          style={{ gridTemplateColumns: "1fr 1.1fr" }}
        >
          <div className="relative">
            <span className="mono text-[11px] text-muted tracking-[0.16em] uppercase mb-[18px] block">
              § 04 — Ask anything
            </span>
            <h2
              className="display text-[clamp(32px,4vw,48px)] m-0 mb-5 text-ink"
            >
              Show, don&apos;t{" "}
              <span className="display-italic text-blue">
                spell.
              </span>
            </h2>
            <p className="text-muted text-[16.5px] leading-[1.55] m-0 mb-7 max-w-[460px]">
              Snap, film, drag, or type. PawPilot reads the same things a vet would in the exam room
              — and cites its sources, every time.
            </p>
            <ChatBubble />
          </div>

          <div className="grid gap-[14px]" style={{ gridTemplateColumns: "1fr 1fr" }}>
            {tiles.map((tile, index) => (
              <div
                key={index}
                className="bg-surface border border-(--hairline) rounded-[18px] p-5 min-h-[180px] flex flex-col justify-between relative overflow-hidden"
              >
                <span
                  className="w-10 h-10 rounded-[12px] bg-(--paper) border border-(--hairline) inline-flex items-center justify-center"
                  style={{ color: tile.iconColor }}
                >
                  <tile.Icon />
                </span>
                <div>
                  <div className="display text-[20px] font-medium text-ink leading-[1.2] mb-1">
                    {tile.label}
                  </div>
                  <div className="mono text-[11.5px] text-muted tracking-[0.02em]">
                    {tile.subtitle}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
