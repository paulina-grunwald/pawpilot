"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

type FloatingDockValue = {
  /** Whether the floating chat panel is currently open. */
  chatOpen: boolean;
  setChatOpen: (open: boolean) => void;
};

/**
 * Coordinates the stacked floating buttons in the bottom-right corner. The chat
 * widget publishes its open state here so the journal FAB can step out of the
 * way while the chat panel is expanded. The default value is inert so either
 * consumer still works when rendered without a provider (e.g. in unit tests).
 */
const FloatingDockContext = createContext<FloatingDockValue>({
  chatOpen: false,
  setChatOpen: () => {},
});

export function useFloatingDock(): FloatingDockValue {
  return useContext(FloatingDockContext);
}

export function FloatingDockProvider({ children }: { children: ReactNode }) {
  const [chatOpen, setChatOpen] = useState(false);
  const value = useMemo(() => ({ chatOpen, setChatOpen }), [chatOpen]);
  return <FloatingDockContext.Provider value={value}>{children}</FloatingDockContext.Provider>;
}
