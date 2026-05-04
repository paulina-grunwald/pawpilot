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
        background: scrolled
          ? "color-mix(in srgb, var(--paper) 85%, transparent)"
          : "transparent",
        backdropFilter: scrolled ? "blur(8px)" : "none",
      }}
    >
      <div className="container-x flex items-center justify-between h-[72px]">
        <Link
          href="/"
          aria-label="PawPilot — home"
          className="flex items-center gap-[10px] no-underline text-ink"
        >
          <PawMark size={56} />
          <span className="display text-[22px] font-semibold tracking-[-0.01em]">
            PawPilot
          </span>
        </Link>
        <nav className="flex gap-7 items-center">
          <a
            href="#how"
            className="text-muted no-underline text-[14px] font-medium"
          >
            How it works
          </a>
          <a
            href="#why"
            className="text-muted no-underline text-[14px] font-medium"
          >
            Why PawPilot
          </a>
          <a
            href="#trust"
            className="text-muted no-underline text-[14px] font-medium"
          >
            The science
          </a>
          <a
            href="#waitlist"
            className="bg-ink text-paper px-4 py-[9px] rounded-full text-[14px] font-medium no-underline inline-flex items-center gap-[6px]"
          >
            Join waitlist <ArrowRightIcon />
          </a>
        </nav>
      </div>
    </header>
  );
}
