type Step = {
  number: string;
  title: string;
  subtitle: string;
  body: string;
};

const steps: Step[] = [
  {
    number: "01",
    title: "Pair the collar.",
    subtitle: "Two minutes, one OAuth screen.",
    body: "Authorize Tractive once. PawPilot starts pulling activity and sleep history retroactively — no waiting.",
  },
  {
    number: "02",
    title: "Build Haru's normal.",
    subtitle: "Quietly, in the background, for 14–30 days.",
    body: 'We learn what energetic looks like for your dog specifically. A senior pug and a 2yr Vizsla have different "normal."',
  },
  {
    number: "03",
    title: "Ask, or get pinged.",
    subtitle: "Whichever comes first.",
    body: '"Did Haru just eat a grape?" → answered now. Activity dips three days running → you hear about it before you would have.',
  },
];

export function HowItWorks() {
  return (
    <section
      id="how"
      style={{
        paddingTop: 96,
        paddingBottom: 96,
        background: "var(--forest)",
        color: "var(--paper)",
        position: "relative",
      }}
    >
      <div className="container-x">
        <div
          className="how-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1.6fr",
            gap: 64,
            alignItems: "start",
          }}
        >
          <div>
            <span
              className="mono"
              style={{
                fontSize: 11,
                color: "rgba(250,247,242,0.55)",
                letterSpacing: "0.16em",
                textTransform: "uppercase",
                marginBottom: 18,
                display: "block",
              }}
            >
              § 03 — How it works
            </span>
            <h2
              className="display"
              style={{
                fontSize: "clamp(36px, 4.4vw, 60px)",
                margin: "0 0 20px",
                color: "var(--paper)",
              }}
            >
              Set it up in the time it takes to{" "}
              <span className="display-italic" style={{ color: "var(--blue-2)" }}>
                brew coffee.
              </span>
            </h2>
            <p
              style={{
                color: "rgba(250,247,242,0.7)",
                fontSize: 17,
                maxWidth: 380,
                margin: 0,
              }}
            >
              No camera in the food bowl. No subscription on a new device. PawPilot is software that
              makes your dog&apos;s existing collar quietly smarter.
            </p>
          </div>

          <ol
            style={{
              listStyle: "none",
              margin: 0,
              padding: 0,
              display: "flex",
              flexDirection: "column",
              gap: 4,
            }}
          >
            {steps.map((step, index) => (
              <li
                key={index}
                style={{
                  display: "grid",
                  gridTemplateColumns: "90px 1fr",
                  gap: 24,
                  padding: "28px 0",
                  borderTop: "1px solid rgba(250,247,242,0.16)",
                  borderBottom:
                    index === steps.length - 1
                      ? "1px solid rgba(250,247,242,0.16)"
                      : "none",
                }}
              >
                <div
                  className="display"
                  style={{
                    fontSize: 56,
                    color: "var(--blue-2)",
                    fontWeight: 400,
                    lineHeight: 1,
                    fontStyle: "italic",
                  }}
                >
                  {step.number}
                </div>
                <div>
                  <h3
                    className="display"
                    style={{
                      fontSize: 26,
                      margin: "0 0 4px",
                      color: "var(--paper)",
                      fontWeight: 500,
                    }}
                  >
                    {step.title}
                  </h3>
                  <div
                    className="display-italic"
                    style={{ fontSize: 16, color: "var(--blue-2)", marginBottom: 10 }}
                  >
                    {step.subtitle}
                  </div>
                  <p
                    style={{
                      color: "rgba(250,247,242,0.7)",
                      fontSize: 15,
                      margin: 0,
                      lineHeight: 1.55,
                      maxWidth: 540,
                    }}
                  >
                    {step.body}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
