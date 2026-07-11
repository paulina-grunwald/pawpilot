import { afterEach, describe, expect, it, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { activePetStorageKey } from "@/lib/activePet";
import { DashboardRedirect } from "./DashboardRedirect";

const { replaceMock } = vi.hoisted(() => ({ replaceMock: vi.fn<(href: string) => void>() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: replaceMock, prefetch: vi.fn() }),
}));

const USER_ID = "user-uuid";

afterEach(() => {
  replaceMock.mockReset();
  window.localStorage.clear();
});

describe("DashboardRedirect", () => {
  it("redirects to the stored active pet when it is still valid", async () => {
    window.localStorage.setItem(activePetStorageKey(USER_ID), "pet-2");
    render(<DashboardRedirect userId={USER_ID} petIds={["pet-1", "pet-2"]} />);
    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/dashboard/pet-2"));
  });

  it("falls back to the first pet when the stored id is stale", async () => {
    window.localStorage.setItem(activePetStorageKey(USER_ID), "pet-deleted");
    render(<DashboardRedirect userId={USER_ID} petIds={["pet-1", "pet-2"]} />);
    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/dashboard/pet-1"));
  });

  it("falls back to the first pet when nothing is stored", async () => {
    render(<DashboardRedirect userId={USER_ID} petIds={["pet-1", "pet-2"]} />);
    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/dashboard/pet-1"));
  });
});
