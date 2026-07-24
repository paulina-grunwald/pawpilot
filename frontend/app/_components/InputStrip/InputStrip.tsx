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
          className="mm-grid grid items-center gap-20"
          style={{ gridTemplateColumns: "1fr 1.1fr" }}
        >
          <div className="relative">
            <span className="mono text-muted mb-[18px] block text-[11px] tracking-[0.16em] uppercase">
              § 04 — Ask anything
            </span>
            <h2 className="display text-ink m-0 mb-5 text-[clamp(32px,4vw,48px)]">
              Show, don&apos;t <span className="display-italic text-blue">spell.</span>
            </h2>
            <p className="text-muted m-0 mb-7 max-w-[460px] text-[16.5px] leading-[1.55]">
              Snap, film, drag, or type. PawPilot reads the same things a vet would in the exam room
              — and cites its sources, every time.
            </p>
            <ChatBubble />
          </div>

          <div className="grid gap-[14px]" style={{ gridTemplateColumns: "1fr 1fr" }}>
            {tiles.map((tile, index) => (
              <div
                key={index}
                className="bg-surface relative flex min-h-[180px] flex-col justify-between overflow-hidden rounded-[18px] border border-(--hairline) p-5"
              >
                <span
                  className="inline-flex h-10 w-10 items-center justify-center rounded-[12px] border border-(--hairline) bg-(--paper)"
                  style={{ color: tile.iconColor }}
                >
                  <tile.Icon />
                </span>
                <div>
                  <div className="display text-ink mb-1 text-[20px] leading-[1.2] font-medium">
                    {tile.label}
                  </div>
                  <div className="mono text-muted text-[11.5px] tracking-[0.02em]">
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
