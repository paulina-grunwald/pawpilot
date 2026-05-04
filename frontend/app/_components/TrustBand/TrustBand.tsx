import Image from "next/image";

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
      className="pt-20 pb-20 bg-surface border-t border-b border-(--hairline) overflow-hidden"
    >
      <div className="container-x">
        <div
          className="trust-grid grid gap-16 items-center"
          style={{ gridTemplateColumns: "1.4fr 1fr" }}
        >
          <div>
            <span className="mono text-[11px] text-muted tracking-[0.16em] uppercase mb-[18px] block">
              § 05 — A note on what this is
            </span>
            <h2
              className="display text-[clamp(30px,3.6vw,44px)] m-0 mb-5 text-ink max-w-[620px]"
            >
              We are not your vet.
              <br />
              <span className="display-italic text-forest">
                We&apos;re a smarter first call.
              </span>
            </h2>
            <p className="text-muted text-[16px] leading-[1.6] m-0 mb-6 max-w-[540px]">
              Every answer cites peer-reviewed veterinary sources. Anything urgent gets routed to
              &ldquo;go now,&rdquo; with the nearest emergency clinic and what to tell them on the
              way. Anything truly unclear we say so out loud.
            </p>
            <div className="flex flex-wrap gap-2">
              {pillLabels.map((label) => (
                <span
                  key={label}
                  className="text-[13px] text-ink px-[14px] py-[7px] rounded-full bg-(--paper) border border-(--hairline-strong)"
                >
                  {label}
                </span>
              ))}
            </div>
          </div>

          <div className="relative min-h-[320px]">
            <div
              className="absolute top-5 right-[60px] bg-(--paper) p-[10px] pb-8 border border-(--hairline) shadow-[0_14px_30px_-10px_color-mix(in_srgb,var(--ink)_18%,transparent)]"
              style={{ transform: "rotate(6deg)" }}
            >
              <Image
                src="/img/aussie-running.png"
                alt="An Australian shepherd mid-run"
                width={220}
                height={160}
                style={{
                  display: "block",
                  objectFit: "cover",
                  width: 220,
                  height: 160,
                  filter: "saturate(0.92)",
                }}
              />
              <div className="mono text-[10px] text-muted text-center mt-2">
                14 hr sleep · normal for her
              </div>
            </div>
            <div
              className="absolute top-[110px] right-0 bg-(--paper) p-[10px] pb-8 border border-(--hairline) shadow-[0_14px_30px_-10px_color-mix(in_srgb,var(--ink)_22%,transparent)]"
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
              <div className="mono text-[10px] text-muted text-center mt-2">
                head tilt · context, please
              </div>
            </div>
          </div>
        </div>

        <div className="mt-14 pt-7 border-t border-(--hairline)">
          <div className="mono text-[11px] text-muted tracking-[0.14em] uppercase mb-[14px]">
            Knowledge corpus drawn from
          </div>
          <div
            className="overflow-hidden"
            style={{
              maskImage: "linear-gradient(90deg, transparent, black 6%, black 94%, transparent)",
            }}
          >
            <div
              className="flex gap-14 w-fit"
              style={{ animation: "scroll-x 32s linear infinite" }}
            >
              {tickerSources.map((source, index) => (
                <span
                  key={index}
                  className="display text-[26px] text-forest font-medium whitespace-nowrap opacity-85"
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
