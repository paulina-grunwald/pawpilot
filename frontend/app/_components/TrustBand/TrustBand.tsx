import Image from "next/image";
import { PawMark } from "../PawMark";

const sources = [
  "WSAVA",
  "AAHA",
  "ACVIM",
  "Veterinary Information Network",
  "Merck Veterinary Manual",
  "JAVMA",
];

const tickerSources = [...sources, ...sources, ...sources];

const pillLabels = ["Cited answers", "Urgency-classified", "Vet-reviewed corpus"];

export function TrustBand() {
  return (
    <section
      id="trust"
      className="bg-surface overflow-hidden border-t border-b border-(--hairline) pt-20 pb-20"
    >
      <div className="container-x">
        <div
          className="trust-grid grid items-center gap-16"
          style={{ gridTemplateColumns: "1.4fr 1fr" }}
        >
          <div>
            <span className="mono text-muted mb-[18px] block text-[11px] tracking-[0.16em] uppercase">
              § 05 — A note on what this is
            </span>
            <h2 className="display text-ink m-0 mb-5 max-w-[620px] text-[clamp(30px,3.6vw,44px)]">
              We are not your vet.
              <br />
              <span className="display-italic text-forest">We&apos;re a smarter first call.</span>
            </h2>
            <p className="text-muted m-0 mb-6 max-w-[540px] text-[16px] leading-[1.6]">
              Every answer cites peer-reviewed veterinary sources. Anything urgent gets routed to
              &ldquo;go now,&rdquo; with the nearest emergency clinic and what to tell them on the
              way. Anything truly unclear we say so out loud.
            </p>
            <div className="flex flex-wrap gap-2">
              {pillLabels.map((label) => (
                <span
                  key={label}
                  className="text-ink rounded-full border border-(--hairline-strong) bg-(--paper) px-[14px] py-[7px] text-[13px]"
                >
                  {label}
                </span>
              ))}
            </div>
          </div>

          <div className="relative min-h-[320px]">
            <div
              className="absolute -top-6 left-0 z-[1] text-center"
              style={{
                transform: "rotate(-6deg)",
                filter: "drop-shadow(0 18px 30px color-mix(in srgb, var(--ink) 20%, transparent))",
              }}
            >
              <PawMark size={220} />
              <div className="mono text-muted mt-3 text-[11px]">smart answers · healthier dogs</div>
            </div>
            <div
              className="absolute top-[110px] right-0 z-[2] border border-(--hairline) bg-(--paper) p-[10px] pb-8 shadow-[0_14px_30px_-10px_color-mix(in_srgb,var(--ink)_22%,transparent)]"
              style={{ transform: "rotate(-5deg)" }}
            >
              <Image
                src="/img/owner-and-dog.jpeg"
                alt="A dog looking up at the camera"
                width={200}
                height={180}
                style={{
                  display: "block",
                  objectFit: "cover",
                  width: 200,
                  height: 180,
                  filter: "saturate(0.92)",
                }}
              />
              <div className="mono text-muted mt-2 text-center text-[10px] leading-normal"></div>
            </div>
          </div>
        </div>

        <div className="border-hairline mt-14 border-t pt-7">
          <div className="mono text-muted mb-[14px] text-[11px] tracking-[0.14em] uppercase">
            Knowledge corpus drawn from
          </div>
          <div
            className="overflow-hidden"
            style={{
              maskImage: "linear-gradient(90deg, transparent, black 6%, black 94%, transparent)",
            }}
          >
            <div
              className="flex w-fit gap-14"
              style={{ animation: "scroll-x 32s linear infinite" }}
            >
              {tickerSources.map((source, index) => (
                <span
                  key={index}
                  className="display text-forest text-[26px] font-medium whitespace-nowrap opacity-85"
                >
                  {source} <span className="text-blue mx-2">·</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
