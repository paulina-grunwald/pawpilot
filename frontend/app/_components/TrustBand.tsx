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
      style={{
        paddingTop: 80,
        paddingBottom: 80,
        background: "var(--surface)",
        borderTop: "1px solid var(--hairline)",
        borderBottom: "1px solid var(--hairline)",
        overflow: "hidden",
      }}
    >
      <div className="container-x">
        <div
          className="trust-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "1.4fr 1fr",
            gap: 64,
            alignItems: "center",
          }}
        >
          <div>
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
              § 05 — A note on what this is
            </span>
            <h2
              className="display"
              style={{
                fontSize: "clamp(30px, 3.6vw, 44px)",
                margin: "0 0 20px",
                color: "var(--ink)",
                maxWidth: 620,
              }}
            >
              We are not your vet.
              <br />
              <span className="display-italic" style={{ color: "var(--forest)" }}>
                We&apos;re a smarter first call.
              </span>
            </h2>
            <p
              style={{
                color: "var(--muted)",
                fontSize: 16,
                lineHeight: 1.6,
                margin: "0 0 24px",
                maxWidth: 540,
              }}
            >
              Every answer cites peer-reviewed veterinary sources. Anything urgent gets routed to
              &ldquo;go now,&rdquo; with the nearest emergency clinic and what to tell them on the
              way. Anything truly unclear we say so out loud.
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {pillLabels.map((label) => (
                <span
                  key={label}
                  style={{
                    fontSize: 13,
                    color: "var(--ink)",
                    padding: "7px 14px",
                    borderRadius: 999,
                    background: "var(--paper)",
                    border: "1px solid var(--hairline-strong)",
                  }}
                >
                  {label}
                </span>
              ))}
            </div>
          </div>

          <div style={{ position: "relative", minHeight: 320 }}>
            <div
              style={{
                position: "absolute",
                top: 20,
                right: 60,
                transform: "rotate(6deg)",
                background: "var(--paper)",
                padding: 10,
                paddingBottom: 32,
                border: "1px solid var(--hairline)",
                boxShadow: "0 14px 30px -10px rgba(31,27,22,0.18)",
              }}
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
              <div
                className="mono"
                style={{
                  fontSize: 10,
                  color: "var(--muted)",
                  textAlign: "center",
                  marginTop: 8,
                }}
              >
                14 hr sleep · normal for her
              </div>
            </div>
            <div
              style={{
                position: "absolute",
                top: 110,
                right: 0,
                transform: "rotate(-5deg)",
                background: "var(--paper)",
                padding: 10,
                paddingBottom: 32,
                border: "1px solid var(--hairline)",
                boxShadow: "0 14px 30px -10px rgba(31,27,22,0.22)",
              }}
            >
              <Image
                src="/img/doggo.jpeg"
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
              <div
                className="mono"
                style={{
                  fontSize: 10,
                  color: "var(--muted)",
                  textAlign: "center",
                  marginTop: 8,
                }}
              >
                head tilt · context, please
              </div>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 56, paddingTop: 28, borderTop: "1px solid var(--hairline)" }}>
          <div
            className="mono"
            style={{
              fontSize: 11,
              color: "var(--muted)",
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              marginBottom: 14,
            }}
          >
            Knowledge corpus drawn from
          </div>
          <div
            style={{
              overflow: "hidden",
              maskImage: "linear-gradient(90deg, transparent, black 6%, black 94%, transparent)",
            }}
          >
            <div
              style={{
                display: "flex",
                gap: 56,
                animation: "scroll-x 32s linear infinite",
                width: "fit-content",
              }}
            >
              {tickerSources.map((source, index) => (
                <span
                  key={index}
                  className="display"
                  style={{
                    fontSize: 26,
                    color: "var(--forest)",
                    fontWeight: 500,
                    whiteSpace: "nowrap",
                    opacity: 0.85,
                  }}
                >
                  {source} <span style={{ color: "var(--blue)", margin: "0 8px" }}>·</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
