"use client";

import { useState, type FormEvent } from "react";
import { HeroDashboardCard } from "../HeroDashboardCard";
import { Polaroid } from "../Polaroid";
import { Sticker } from "../Sticker";
import { ArrowRightIcon, CheckIcon } from "../icons";

type Status = "idle" | "sending" | "done" | "error";

const HARU_PORTRAIT = "/img/sunset-dog.webp";
const OWNER_AND_HARU = "/img/owner-and-dog.jpeg";

export function Hero() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setErrorMessage("That email doesn't quite look right.");
      setStatus("error");
      return;
    }
    setStatus("sending");
    setTimeout(() => setStatus("done"), 700);
  };

  const sendDisabled = status === "sending" || status === "done";

  return (
    <section className="pt-14 pb-20 relative overflow-hidden">
      <div className="container-x relative">
        <div className="flex justify-center mb-7">
          <span className="inline-flex items-center gap-2 px-[14px] py-[6px] rounded-full bg-surface border border-(--hairline) text-[12px] font-medium text-ink">
            <span
              className="w-[6px] h-[6px] rounded-full bg-blue"
              style={{ animation: "pulse-dot 1.6s infinite" }}
            />
            <span className="mono tracking-[0.06em]">
              NOW IN PRIVATE BETA · 1,247 DOGS
            </span>
          </span>
        </div>

        <h1
          className="display text-center mx-auto mb-7 max-w-[1000px] text-[clamp(44px,7vw,96px)] leading-[0.98] tracking-[-0.035em] font-semibold text-ink"
        >
          For the dog you
          <br />
          can&apos;t stop{" "}
          <em
            className="display-italic underline-wave font-semibold text-blue"
          >
            worrying
          </em>{" "}
          about.
        </h1>

        <p className="text-center max-w-[640px] mx-auto mb-9 text-[19px] text-muted leading-[1.55]">
          PawPilot watches their patterns, learns{" "}
          <em className="display-italic text-ink">
            their
          </em>{" "}
          normal — not the breed average — and tells you the morning something drifts. Not the week
          after you start to worry.
        </p>

        <form
          onSubmit={submit}
          id="waitlist"
          className="flex justify-center gap-2 max-w-[480px] mx-auto mb-[14px] flex-wrap relative"
          suppressHydrationWarning
        >
          <label htmlFor="email-hero" className="absolute left-[-9999px]">
            Email
          </label>
          <input
            id="email-hero"
            type="email"
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
              if (status === "error") setStatus("idle");
            }}
            placeholder="you@yourdog.house"
            disabled={sendDisabled}
            className="focus-ring flex-[1_1_240px] min-w-[240px] px-[18px] py-[14px] text-[15px] rounded-full bg-(--card) font-[inherit] outline-none text-ink"
            style={{
              border: `1.5px solid ${status === "error" ? "var(--terracotta)" : "var(--ink)"}`,
            }}
          />
          <button
            type="submit"
            disabled={sendDisabled}
            aria-live="polite"
            className="px-6 py-[14px] rounded-full border-none text-paper text-[15px] font-semibold inline-flex items-center gap-[6px] shadow-[0_6px_20px_-8px_color-mix(in_srgb,var(--blue)_60%,transparent)]"
            style={{
              background: status === "done" ? "var(--forest)" : "var(--blue)",
            }}
          >
            {status === "idle" && (
              <>
                Save my spot <ArrowRightIcon />
              </>
            )}
            {status === "sending" && "Sending…"}
            {status === "done" && (
              <>
                <CheckIcon /> You&apos;re in
              </>
            )}
            {status === "error" && "Try again"}
          </button>
        </form>

        <div
          className="hand text-center text-[19px] mb-14"
          style={{ color: status === "error" ? "var(--terracotta)" : "var(--muted)" }}
        >
          {status === "error"
            ? errorMessage
            : "free during beta · no card · we won't spam, pinky promise"}
        </div>

        <div
          className="hero-cast relative max-w-[1000px] mx-auto grid gap-8 items-center justify-items-center"
          style={{ gridTemplateColumns: "1fr 1fr 1fr" }}
        >
          <div className="relative">
            <Polaroid
              src={HARU_PORTRAIT}
              alt="Haru, an Australian shepherd, at sunset"
              caption="Haru · 6yo"
              rotate={-5}
              objectPosition="50% 40%"
              sticker={
                <Sticker color="var(--blue)" rotate={-10} top={-12} right={-14}>
                  The boss
                </Sticker>
              }
            />
          </div>
          <div style={{ marginTop: -40 }}>
            <HeroDashboardCard />
          </div>
          <div>
            <Polaroid
              src={OWNER_AND_HARU}
              alt="The owner with Haru late at night"
              caption="me & her, 11pm"
              rotate={6}
              objectPosition="40% 30%"
              sticker={
                <Sticker color="var(--warm)" rotate={8} bottom={-14} left={-14}>
                  The worrier
                </Sticker>
              }
            />
          </div>
        </div>
      </div>
    </section>
  );
}
