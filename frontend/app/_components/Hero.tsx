"use client";

import { useState, type FormEvent } from "react";
import { HeroDashboardCard } from "./HeroDashboardCard";
import { Polaroid } from "./Polaroid";
import { Sticker } from "./Sticker";
import { ArrowRightIcon, CheckIcon } from "./icons";

type Status = "idle" | "sending" | "done" | "error";

const HARU_PORTRAIT = "/img/sunset-dog.png";
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
    <section
      style={{
        paddingTop: 56,
        paddingBottom: 80,
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div className="container-x" style={{ position: "relative" }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 28 }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "6px 14px",
              borderRadius: 999,
              background: "var(--surface)",
              border: "1px solid var(--hairline)",
              fontSize: 12,
              fontWeight: 500,
              color: "var(--ink)",
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: "var(--blue)",
                animation: "pulse-dot 1.6s infinite",
              }}
            />
            <span className="mono" style={{ letterSpacing: "0.06em" }}>
              NOW IN PRIVATE BETA · 1,247 DOGS
            </span>
          </span>
        </div>

        <h1
          className="display"
          style={{
            textAlign: "center",
            margin: "0 auto 28px",
            maxWidth: 1000,
            fontSize: "clamp(44px, 7vw, 96px)",
            lineHeight: 0.98,
            letterSpacing: "-0.035em",
            fontWeight: 600,
            color: "var(--ink)",
          }}
        >
          For the dog you
          <br />
          can&apos;t stop{" "}
          <em
            className="display-italic underline-wave"
            style={{ fontWeight: 600, color: "var(--blue)" }}
          >
            worrying
          </em>{" "}
          about.
        </h1>

        <p
          style={{
            textAlign: "center",
            maxWidth: 640,
            margin: "0 auto 36px",
            fontSize: 19,
            color: "var(--muted)",
            lineHeight: 1.55,
          }}
        >
          PawPilot watches their patterns, learns{" "}
          <em className="display-italic" style={{ color: "var(--ink)" }}>
            their
          </em>{" "}
          normal — not the breed average — and tells you the morning something drifts. Not the week
          after you start to worry.
        </p>

        <form
          onSubmit={submit}
          id="waitlist"
          style={{
            display: "flex",
            justifyContent: "center",
            gap: 8,
            maxWidth: 480,
            margin: "0 auto 14px",
            flexWrap: "wrap",
          }}
        >
          <label htmlFor="email-hero" style={{ position: "absolute", left: -9999 }}>
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
            className="focus-ring"
            style={{
              flex: "1 1 240px",
              minWidth: 240,
              padding: "14px 18px",
              fontSize: 15,
              border: `1.5px solid ${status === "error" ? "var(--terracotta)" : "var(--ink)"}`,
              borderRadius: 999,
              background: "var(--card)",
              fontFamily: "inherit",
              outline: "none",
              color: "var(--ink)",
            }}
          />
          <button
            type="submit"
            disabled={sendDisabled}
            style={{
              padding: "14px 24px",
              borderRadius: 999,
              border: "none",
              background: status === "done" ? "var(--forest)" : "var(--blue)",
              color: "#fff",
              fontSize: 15,
              fontWeight: 600,
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              boxShadow: "0 6px 20px -8px color-mix(in srgb, var(--blue) 60%, transparent)",
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
          className="hand"
          style={{
            textAlign: "center",
            fontSize: 19,
            color: status === "error" ? "var(--terracotta)" : "var(--muted)",
            marginBottom: 56,
          }}
        >
          {status === "error"
            ? errorMessage
            : "free during beta · no card · we won't spam, pinky promise"}
        </div>

        <div
          className="hero-cast"
          style={{
            position: "relative",
            maxWidth: 1000,
            margin: "0 auto",
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1fr",
            gap: 32,
            alignItems: "center",
            justifyItems: "center",
          }}
        >
          <div style={{ position: "relative" }}>
            <Polaroid
              src={HARU_PORTRAIT}
              alt="Haru, an Australian shepherd, at sunset"
              caption="Haru · 6yo"
              rotate={-5}
              unoptimized={false}
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
              unoptimized={false}
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
