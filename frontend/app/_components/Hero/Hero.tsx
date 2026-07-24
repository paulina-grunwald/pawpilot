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
    <section className="relative overflow-hidden pt-14 pb-20">
      <div className="container-x relative">
        <div className="mb-7 flex justify-center">
          <span className="bg-surface text-ink inline-flex items-center gap-2 rounded-full border border-(--hairline) px-[14px] py-[6px] text-[12px] font-medium">
            <span
              className="bg-blue h-[6px] w-[6px] rounded-full"
              style={{ animation: "pulse-dot 1.6s infinite" }}
            />
            <span className="mono tracking-[0.06em]">NOW IN PRIVATE BETA · 1,247 DOGS</span>
          </span>
        </div>

        <h1 className="display text-ink mx-auto mb-7 max-w-[1000px] text-center text-[clamp(44px,7vw,96px)] leading-[0.98] font-semibold tracking-[-0.035em]">
          For the dog you
          <br />
          can&apos;t stop{" "}
          <em className="display-italic underline-wave text-blue font-semibold">worrying</em> about.
        </h1>

        <p className="text-muted mx-auto mb-9 max-w-[640px] text-center text-[19px] leading-[1.55]">
          PawPilot watches their patterns, learns <em className="display-italic text-ink">their</em>{" "}
          normal — not the breed average — and tells you the morning something drifts. Not the week
          after you start to worry.
        </p>

        <form
          onSubmit={submit}
          id="waitlist"
          className="relative mx-auto mb-[14px] flex max-w-[480px] flex-wrap justify-center gap-2"
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
            className="focus-ring text-ink min-w-[240px] flex-[1_1_240px] rounded-full bg-(--card) px-[18px] py-[14px] font-[inherit] text-[15px] outline-none"
            style={{
              border: `1.5px solid ${status === "error" ? "var(--terracotta)" : "var(--ink)"}`,
            }}
          />
          <button
            type="submit"
            disabled={sendDisabled}
            aria-live="polite"
            className="text-paper inline-flex items-center gap-[6px] rounded-full border-none px-6 py-[14px] text-[15px] font-semibold shadow-[0_6px_20px_-8px_color-mix(in_srgb,var(--blue)_60%,transparent)]"
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
          className="hand mb-14 text-center text-[19px]"
          style={{ color: status === "error" ? "var(--terracotta)" : "var(--muted)" }}
        >
          {status === "error"
            ? errorMessage
            : "free during beta · no card · we won't spam, pinky promise"}
        </div>

        <div
          className="hero-cast relative mx-auto grid max-w-[1000px] items-center justify-items-center gap-8"
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
