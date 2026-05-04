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
      className="pt-24 pb-24 bg-forest text-paper relative"
    >
      <div className="container-x">
        <div
          className="how-grid grid gap-16 items-start"
          style={{ gridTemplateColumns: "1fr 1.6fr" }}
        >
          <div>
            <span className="mono text-[11px] text-[color-mix(in_srgb,var(--paper)_55%,transparent)] tracking-[0.16em] uppercase mb-[18px] block">
              § 03 — How it works
            </span>
            <h2
              className="display text-[clamp(36px,4.4vw,60px)] m-0 mb-5 text-paper"
            >
              Set it up in the time it takes to{" "}
              <span className="display-italic text-(--blue-2)">
                brew coffee.
              </span>
            </h2>
            <p className="text-[color-mix(in_srgb,var(--paper)_70%,transparent)] text-[17px] max-w-[380px] m-0">
              No camera in the food bowl. No subscription on a new device. PawPilot is software that
              makes your dog&apos;s existing collar quietly smarter.
            </p>
          </div>

          <ol className="list-none m-0 p-0 flex flex-col gap-1">
            {steps.map((step, index) => (
              <li
                key={index}
                className="grid gap-6 py-7 border-t border-[color-mix(in_srgb,var(--paper)_16%,transparent)]"
                style={{
                  gridTemplateColumns: "90px 1fr",
                  borderBottom:
                    index === steps.length - 1
                      ? "1px solid color-mix(in srgb, var(--paper) 16%, transparent)"
                      : "none",
                }}
              >
                <div className="display text-[56px] text-(--blue-2) font-normal leading-none italic">
                  {step.number}
                </div>
                <div>
                  <h3 className="display text-[26px] m-0 mb-1 text-paper font-medium">
                    {step.title}
                  </h3>
                  <div className="display-italic text-[16px] text-(--blue-2) mb-[10px]">
                    {step.subtitle}
                  </div>
                  <p className="text-[color-mix(in_srgb,var(--paper)_70%,transparent)] text-[15px] m-0 leading-[1.55] max-w-[540px]">
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
