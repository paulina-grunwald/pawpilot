"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PawMark } from "../PawMark";
import { ArrowRightIcon } from "../icons";

export function Nav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className="sticky top-0 z-50 transition-all duration-200 ease-[ease]"
      style={{
        borderBottom: scrolled ? "1px solid var(--hairline)" : "1px solid transparent",
        background: scrolled ? "color-mix(in srgb, var(--paper) 85%, transparent)" : "transparent",
        backdropFilter: scrolled ? "blur(8px)" : "none",
      }}
    >
      <div className="container-x flex h-[72px] items-center justify-between">
        <Link
          href="/"
          aria-label="PawPilot — home"
          className="text-ink flex items-center gap-[10px] no-underline"
        >
          <PawMark size={56} />
          <span className="display text-[22px] font-semibold tracking-[-0.01em]">PawPilot</span>
        </Link>
        <nav className="flex items-center gap-7">
          <a href="#how" className="text-muted text-[14px] font-medium no-underline">
            How it works
          </a>
          <a href="#why" className="text-muted text-[14px] font-medium no-underline">
            Why PawPilot
          </a>
          <a href="#trust" className="text-muted text-[14px] font-medium no-underline">
            The science
          </a>
          <Link
            href="/login"
            className="inline-flex items-center gap-1.5 rounded-full px-6 py-3.5 text-[15px] font-semibold no-underline shadow-[0_6px_20px_-8px_color-mix(in_srgb,var(--blue)_60%,transparent)]"
            style={{ background: "var(--blue)", color: "var(--paper)" }}
          >
            Log in <ArrowRightIcon />
          </Link>
        </nav>
      </div>
    </header>
  );
}
