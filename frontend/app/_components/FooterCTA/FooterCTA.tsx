"use client";

import { useState, type FormEvent } from "react";
import { PawMark } from "../PawMark";
import { ArrowRightIcon, CheckIcon } from "../icons";

type Status = "idle" | "sending" | "done";

export function FooterCTA() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>("idle");

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return;
    setStatus("sending");
    setTimeout(() => setStatus("done"), 600);
  };

  const sendDisabled = status === "sending" || status === "done";

  return (
    <footer className="bg-ink text-paper relative overflow-hidden">
      <div className="pt-24 pb-14">
        <div className="container-x">
          <div className="max-w-[880px]">
            <span className="mono mb-[18px] block text-[11px] tracking-[0.16em] text-[color-mix(in_srgb,var(--paper)_50%,transparent)] uppercase">
              § 06 — One last thing
            </span>
            <h2 className="display text-paper m-0 mb-8 text-[clamp(48px,7vw,96px)] leading-[0.98]">
              Your dog will <span className="display-italic text-(--blue-2)">thank you.</span>
              <br />
              Probably with a paw on the laptop.
            </h2>

            <form onSubmit={submit} className="relative mb-7 max-w-[540px]">
              <label htmlFor="email-foot" className="absolute left-[-9999px]">
                Email
              </label>
              <div className="flex items-center rounded-full border border-[color-mix(in_srgb,var(--paper)_18%,transparent)] bg-[color-mix(in_srgb,var(--paper)_6%,transparent)] p-[6px]">
                <input
                  id="email-foot"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@yourdog.house"
                  disabled={sendDisabled}
                  className="text-paper flex-1 border-none bg-transparent px-[18px] py-3 font-[inherit] text-[15px] outline-none"
                />
                <button
                  type="submit"
                  disabled={sendDisabled}
                  aria-live="polite"
                  className="text-paper inline-flex items-center gap-[7px] rounded-full border-none px-[22px] py-3 text-[14px] font-semibold"
                  style={{
                    background: status === "done" ? "var(--forest)" : "var(--blue)",
                  }}
                >
                  {status === "idle" && (
                    <>
                      Join the waitlist <ArrowRightIcon />
                    </>
                  )}
                  {status === "sending" && <>Sending…</>}
                  {status === "done" && (
                    <>
                      <CheckIcon /> See you soon
                    </>
                  )}
                </button>
              </div>
            </form>

            <p className="m-0 max-w-[460px] text-[13.5px] text-[color-mix(in_srgb,var(--paper)_55%,transparent)]">
              We onboard ~50 dogs a week. You&apos;ll hear from us when there&apos;s a spot — with
              your dog&apos;s name in the subject line, like a normal human would.
            </p>
          </div>
        </div>
      </div>

      <div className="border-t border-[color-mix(in_srgb,var(--paper)_10%,transparent)] py-7">
        <div className="container-x flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3 text-[color-mix(in_srgb,var(--paper)_70%,transparent)]">
            <PawMark size={40} />
            <span className="display text-[15px] font-medium">PawPilot</span>
            <span className="mono ml-2 text-[11px] text-[color-mix(in_srgb,var(--paper)_40%,transparent)]">
              © 2026 · Made by anxious dog people, for anxious dog people
            </span>
          </div>
          <div className="flex gap-6 text-[13px] text-[color-mix(in_srgb,var(--paper)_55%,transparent)]">
            <a href="/privacy" className="text-inherit no-underline">
              Privacy
            </a>
            <a href="/terms" className="text-inherit no-underline">
              Terms
            </a>
            <a href="mailto:hi@pawpilot.app" className="text-inherit no-underline">
              hi@pawpilot.app
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
