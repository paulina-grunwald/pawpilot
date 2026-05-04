import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

class IntersectionObserverStub {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
  takeRecords = vi.fn(() => []);
  root: Element | null = null;
  rootMargin = "";
  thresholds: ReadonlyArray<number> = [];
}

vi.stubGlobal("IntersectionObserver", IntersectionObserverStub);
