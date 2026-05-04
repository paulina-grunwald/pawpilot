import { AlertCard } from "../AlertCard";

export function PhoneMock() {
  return (
    <div className="relative w-[360px] h-[640px] rounded-[48px] bg-ink p-[10px] shadow-[0_30px_60px_-20px_color-mix(in_srgb,var(--ink)_35%,transparent),_0_0_0_1px_color-mix(in_srgb,var(--ink)_6%,transparent)]">
      <div className="absolute top-[18px] left-1/2 -translate-x-1/2 w-[100px] h-[26px] rounded-[14px] bg-(--black) z-[2]" />
      <div className="w-full h-full rounded-[40px] bg-[linear-gradient(180deg,var(--surface)_0%,var(--paper)_30%)] relative overflow-hidden pt-[54px] px-[18px] pb-6">
        <div className="mono flex justify-between text-[11px] text-ink mb-6 px-3">
          <span>9:41</span>
          <span className="flex gap-1 items-center">
            <span>·•••</span>
            <span>100%</span>
          </span>
        </div>

        <div className="px-[6px] pb-[18px]">
          <div className="mono text-[10px] text-muted tracking-[0.1em] uppercase mb-1">
            Tuesday
          </div>
          <div className="display text-[22px] font-medium text-ink leading-[1.15]">
            Morning.{" "}
            <span className="display-italic text-forest">
              Haru&apos;s a little off.
            </span>
          </div>
        </div>

        <div className="flex justify-center">
          <div style={{ transform: "scale(0.96)", transformOrigin: "top center" }}>
            <AlertCard />
          </div>
        </div>
      </div>
    </div>
  );
}
