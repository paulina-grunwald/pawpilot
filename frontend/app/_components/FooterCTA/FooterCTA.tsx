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
            <span className="mono text-[11px] text-[color-mix(in_srgb,var(--paper)_50%,transparent)] tracking-[0.16em] uppercase mb-[18px] block">
              § 06 — One last thing
            </span>
            <h2
              className="display text-[clamp(48px,7vw,96px)] m-0 mb-8 leading-[0.98] text-paper"
            >
              Your dog will{" "}
              <span className="display-italic text-(--blue-2)">
                thank you.
              </span>
              <br />
              Probably with a paw on the laptop.
            </h2>

            <form onSubmit={submit} className="max-w-[540px] mb-7 relative">
              <label htmlFor="email-foot" className="absolute left-[-9999px]">
                Email
              </label>
              <div className="flex items-center bg-[color-mix(in_srgb,var(--paper)_6%,transparent)] border border-[color-mix(in_srgb,var(--paper)_18%,transparent)] rounded-full p-[6px]">
                <input
                  id="email-foot"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@yourdog.house"
                  disabled={sendDisabled}
                  className="flex-1 border-none bg-transparent px-[18px] py-3 text-[15px] text-paper font-[inherit] outline-none"
                />
                <button
                  type="submit"
                  disabled={sendDisabled}
                  aria-live="polite"
                  className="border-none px-[22px] py-3 rounded-full text-[14px] font-semibold inline-flex items-center gap-[7px] text-paper"
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

            <p className="text-[color-mix(in_srgb,var(--paper)_55%,transparent)] text-[13.5px] max-w-[460px] m-0">
              We onboard ~50 dogs a week. You&apos;ll hear from us when there&apos;s a spot — with
              your dog&apos;s name in the subject line, like a normal human would.
            </p>
          </div>
        </div>
      </div>

      <div className="border-t border-[color-mix(in_srgb,var(--paper)_10%,transparent)] py-7">
        <div className="container-x flex justify-between items-center flex-wrap gap-4">
          <div className="flex items-center gap-3 text-[color-mix(in_srgb,var(--paper)_70%,transparent)]">
            <PawMark size={40} />
            <span className="display text-[15px] font-medium">PawPilot</span>
            <span className="mono text-[11px] text-[color-mix(in_srgb,var(--paper)_40%,transparent)] ml-2">
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
