import type { ComponentType, SVGProps } from "react";
import { ChatBubble } from "./ChatBubble";
import { CamIcon, ChatIcon, DocIcon, FilmIcon } from "./icons";

type Tile = {
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
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
    <section style={{ paddingTop: 96, paddingBottom: 96 }}>
      <div className="container-x">
        <div
          className="mm-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1.1fr",
            gap: 80,
            alignItems: "center",
          }}
        >
          <div style={{ position: "relative" }}>
            <span
              className="mono"
              style={{
                fontSize: 11,
                color: "var(--muted)",
                letterSpacing: "0.16em",
                textTransform: "uppercase",
                marginBottom: 18,
                display: "block",
              }}
            >
              § 04 — Ask anything
            </span>
            <h2
              className="display"
              style={{
                fontSize: "clamp(32px, 4vw, 48px)",
                margin: "0 0 20px",
                color: "var(--ink)",
              }}
            >
              Show, don&apos;t{" "}
              <span className="display-italic" style={{ color: "var(--blue)" }}>
                spell.
              </span>
            </h2>
            <p
              style={{
                color: "var(--muted)",
                fontSize: 16.5,
                lineHeight: 1.55,
                margin: "0 0 28px",
                maxWidth: 460,
              }}
            >
              Snap, film, drag, or type. PawPilot reads the same things a vet would in the exam room
              — and cites its sources, every time.
            </p>
            <ChatBubble />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            {tiles.map((tile, index) => (
              <div
                key={index}
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--hairline)",
                  borderRadius: 18,
                  padding: 20,
                  minHeight: 180,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                <span
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 12,
                    background: "var(--paper)",
                    border: "1px solid var(--hairline)",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: tile.iconColor,
                  }}
                >
                  <tile.Icon />
                </span>
                <div>
                  <div
                    className="display"
                    style={{
                      fontSize: 20,
                      fontWeight: 500,
                      color: "var(--ink)",
                      lineHeight: 1.2,
                      marginBottom: 4,
                    }}
                  >
                    {tile.label}
                  </div>
                  <div
                    className="mono"
                    style={{
                      fontSize: 11.5,
                      color: "var(--muted)",
                      letterSpacing: "0.02em",
                    }}
                  >
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
