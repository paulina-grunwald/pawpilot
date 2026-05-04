"use client";

import { useState, type FormEvent } from "react";
import { PawMark } from "./PawMark";
import { ArrowRightIcon, CheckIcon } from "./icons";

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
    <footer
      style={{
        background: "var(--ink)",
        color: "var(--paper)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div style={{ paddingTop: 96, paddingBottom: 56 }}>
        <div className="container-x">
          <div style={{ maxWidth: 880 }}>
            <span
              className="mono"
              style={{
                fontSize: 11,
                color: "rgba(250,247,242,0.5)",
                letterSpacing: "0.16em",
                textTransform: "uppercase",
                marginBottom: 18,
                display: "block",
              }}
            >
              § 06 — One last thing
            </span>
            <h2
              className="display"
              style={{
                fontSize: "clamp(48px, 7vw, 96px)",
                margin: "0 0 32px",
                lineHeight: 0.98,
                color: "var(--paper)",
              }}
            >
              Your dog will{" "}
              <span className="display-italic" style={{ color: "var(--blue-2)" }}>
                thank you.
              </span>
              <br />
              Probably with a paw on the laptop.
            </h2>

            <form onSubmit={submit} style={{ maxWidth: 540, marginBottom: 28 }}>
              <label htmlFor="email-foot" style={{ position: "absolute", left: -9999 }}>
                Email
              </label>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  background: "rgba(250,247,242,0.06)",
                  border: "1px solid rgba(250,247,242,0.18)",
                  borderRadius: 999,
                  padding: 6,
                }}
              >
                <input
                  id="email-foot"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@yourdog.house"
                  disabled={sendDisabled}
                  style={{
                    flex: 1,
                    border: "none",
                    background: "transparent",
                    padding: "12px 18px",
                    fontSize: 15,
                    color: "var(--paper)",
                    fontFamily: "inherit",
                    outline: "none",
                  }}
                />
                <button
                  type="submit"
                  disabled={sendDisabled}
                  style={{
                    background: status === "done" ? "var(--forest)" : "var(--blue)",
                    color: "var(--paper)",
                    border: "none",
                    padding: "12px 22px",
                    borderRadius: 999,
                    fontSize: 14,
                    fontWeight: 600,
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 7,
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

            <p
              style={{
                color: "rgba(250,247,242,0.55)",
                fontSize: 13.5,
                maxWidth: 460,
                margin: 0,
              }}
            >
              We onboard ~50 dogs a week. You&apos;ll hear from us when there&apos;s a spot — with
              your dog&apos;s name in the subject line, like a normal human would.
            </p>
          </div>
        </div>
      </div>

      <div style={{ borderTop: "1px solid rgba(250,247,242,0.1)", padding: "28px 0" }}>
        <div
          className="container-x"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 16,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              color: "rgba(250,247,242,0.7)",
            }}
          >
            <PawMark size={40} />
            <span className="display" style={{ fontSize: 15, fontWeight: 500 }}>
              PawPilot
            </span>
            <span
              className="mono"
              style={{
                fontSize: 11,
                color: "rgba(250,247,242,0.4)",
                marginLeft: 8,
              }}
            >
              © 2026 · Made by anxious dog people, for anxious dog people
            </span>
          </div>
          <div
            style={{
              display: "flex",
              gap: 24,
              fontSize: 13,
              color: "rgba(250,247,242,0.55)",
            }}
          >
            <a href="#" style={{ color: "inherit", textDecoration: "none" }}>
              Privacy
            </a>
            <a href="#" style={{ color: "inherit", textDecoration: "none" }}>
              Terms
            </a>
            <a href="mailto:hi@pawpilot.app" style={{ color: "inherit", textDecoration: "none" }}>
              hi@pawpilot.app
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
