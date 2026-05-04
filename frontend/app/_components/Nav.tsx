"use client";

import { useEffect, useState } from "react";
import { PawMark } from "./PawMark";
import { ArrowRightIcon } from "./icons";

export function Nav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        borderBottom: scrolled ? "1px solid var(--hairline)" : "1px solid transparent",
        background: scrolled ? "rgba(250,247,242,0.85)" : "transparent",
        backdropFilter: scrolled ? "blur(8px)" : "none",
        transition: "all 200ms ease",
      }}
    >
      <div
        className="container-x"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: 72,
        }}
      >
        <a
          href="#"
          aria-label="PawPilot — home"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            textDecoration: "none",
            color: "var(--ink)",
          }}
        >
          <PawMark size={56} />
          <span
            className="display"
            style={{ fontSize: 22, fontWeight: 600, letterSpacing: "-0.01em" }}
          >
            PawPilot
          </span>
        </a>
        <nav style={{ display: "flex", gap: 28, alignItems: "center" }}>
          <a
            href="#how"
            style={{
              color: "var(--muted)",
              textDecoration: "none",
              fontSize: 14,
              fontWeight: 500,
            }}
          >
            How it works
          </a>
          <a
            href="#why"
            style={{
              color: "var(--muted)",
              textDecoration: "none",
              fontSize: 14,
              fontWeight: 500,
            }}
          >
            Why PawPilot
          </a>
          <a
            href="#trust"
            style={{
              color: "var(--muted)",
              textDecoration: "none",
              fontSize: 14,
              fontWeight: 500,
            }}
          >
            The science
          </a>
          <a
            href="#waitlist"
            style={{
              background: "var(--ink)",
              color: "var(--paper)",
              padding: "9px 16px",
              borderRadius: 999,
              fontSize: 14,
              fontWeight: 500,
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            Join waitlist <ArrowRightIcon />
          </a>
        </nav>
      </div>
    </header>
  );
}
