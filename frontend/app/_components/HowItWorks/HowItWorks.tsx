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
    <section id="how" className="bg-forest text-paper relative pt-24 pb-24">
      <div className="container-x">
        <div
          className="how-grid grid items-start gap-16"
          style={{ gridTemplateColumns: "1fr 1.6fr" }}
        >
          <div>
            <span className="mono mb-[18px] block text-[11px] tracking-[0.16em] text-[color-mix(in_srgb,var(--paper)_55%,transparent)] uppercase">
              § 03 — How it works
            </span>
            <h2 className="display text-paper m-0 mb-5 text-[clamp(36px,4.4vw,60px)]">
              Set it up in the time it takes to{" "}
              <span className="display-italic text-(--blue-2)">brew coffee.</span>
            </h2>
            <p className="m-0 max-w-[380px] text-[17px] text-[color-mix(in_srgb,var(--paper)_70%,transparent)]">
              No camera in the food bowl. No subscription on a new device. PawPilot is software that
              makes your dog&apos;s existing collar quietly smarter.
            </p>
          </div>

          <ol className="m-0 flex list-none flex-col gap-1 p-0">
            {steps.map((step, index) => (
              <li
                key={index}
                className="grid gap-6 border-t border-[color-mix(in_srgb,var(--paper)_16%,transparent)] py-7"
                style={{
                  gridTemplateColumns: "90px 1fr",
                  borderBottom:
                    index === steps.length - 1
                      ? "1px solid color-mix(in srgb, var(--paper) 16%, transparent)"
                      : "none",
                }}
              >
                <div className="display text-[56px] leading-none font-normal text-(--blue-2) italic">
                  {step.number}
                </div>
                <div>
                  <h3 className="display text-paper m-0 mb-1 text-[26px] font-medium">
                    {step.title}
                  </h3>
                  <div className="display-italic mb-[10px] text-[16px] text-(--blue-2)">
                    {step.subtitle}
                  </div>
                  <p className="m-0 max-w-[540px] text-[15px] leading-[1.55] text-[color-mix(in_srgb,var(--paper)_70%,transparent)]">
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
