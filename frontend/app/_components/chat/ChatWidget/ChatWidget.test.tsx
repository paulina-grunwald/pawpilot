import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { PetRead } from "@/lib/pets";
import { ChatWidget } from "./ChatWidget";

const { pathnameMock, listPetsMock } = vi.hoisted(() => ({
  pathnameMock: vi.fn<() => string>(() => "/dashboard"),
  listPetsMock: vi.fn<() => Promise<PetRead[]>>(),
}));

vi.mock("next/navigation", () => ({ usePathname: () => pathnameMock() }));
vi.mock("@/lib/pets", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/pets")>();
  return { ...actual, listPetsForBrowser: listPetsMock };
});

const USER_ID = "user-1";

const samplePet: PetRead = {
  id: "pet-1",
  name: "Luna",
  breed_other: "Aussie",
  birthday: "2021-06-14",
  sex: "female",
  spayed_neutered: true,
  weight_grams: 22000,
  notes: null,
  photo_path: null,
  photo_url: null,
  created_at: "2026-05-23T00:00:00Z",
  updated_at: "2026-05-23T00:00:00Z",
  age_years: 4,
  age_months: 0,
  age_weeks: 200,
  life_stage: "adult",
};

afterEach(() => {
  pathnameMock.mockReturnValue("/dashboard");
  listPetsMock.mockReset();
  window.localStorage.clear();
});

describe("ChatWidget", () => {
  it("shows the launcher and hides the panel until opened", () => {
    render(<ChatWidget userId={USER_ID} />);
    expect(screen.getByRole("button", { name: /ask pawpilot/i })).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("opens the panel and loads the chat on click", async () => {
    listPetsMock.mockResolvedValue([samplePet]);
    const user = userEvent.setup();
    render(<ChatWidget userId={USER_ID} />);

    await user.click(screen.getByRole("button", { name: /ask pawpilot/i }));

    await waitFor(() =>
      expect(screen.getByRole("textbox", { name: /ask pawpilot/i })).toBeInTheDocument(),
    );
    expect(listPetsMock).toHaveBeenCalledTimes(1);
  });

  it("retries loading the dogs after a failure", async () => {
    listPetsMock.mockRejectedValueOnce(new Error("down")).mockResolvedValueOnce([samplePet]);
    const user = userEvent.setup();
    render(<ChatWidget userId={USER_ID} />);

    await user.click(screen.getByRole("button", { name: /ask pawpilot/i }));
    await waitFor(() => expect(screen.getByText(/couldn't load your dogs/i)).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /try again/i }));

    await waitFor(() =>
      expect(screen.getByRole("textbox", { name: /ask pawpilot/i })).toBeInTheDocument(),
    );
    expect(listPetsMock).toHaveBeenCalledTimes(2);
  });

  it("prompts to add a dog when the user has none", async () => {
    listPetsMock.mockResolvedValue([]);
    const user = userEvent.setup();
    render(<ChatWidget userId={USER_ID} />);

    await user.click(screen.getByRole("button", { name: /ask pawpilot/i }));

    await waitFor(() => expect(screen.getByText(/add a dog/i)).toBeInTheDocument());
  });

  it("renders nothing on the dedicated chat page", () => {
    pathnameMock.mockReturnValue("/chat");
    const { container } = render(<ChatWidget userId={USER_ID} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("chats about the dog named in the current route, without a picker", async () => {
    const secondPet: PetRead = { ...samplePet, id: "pet-2", name: "Rex", breed_other: "Beagle" };
    listPetsMock.mockResolvedValue([samplePet, secondPet]);
    pathnameMock.mockReturnValue("/dashboard/pet-2");
    const user = userEvent.setup();
    render(<ChatWidget userId={USER_ID} />);

    await user.click(screen.getByRole("button", { name: /ask pawpilot/i }));

    await waitFor(() => expect(screen.getByText("Rex")).toBeInTheDocument());
    expect(screen.getByText(/every answer cites its sources/i)).toHaveTextContent(/about Rex/i);
    // The picker is gone: the dog is derived from the URL, not chosen.
    expect(screen.queryByRole("button", { name: /pick a dog|luna|rex/i })).not.toBeInTheDocument();
  });
});
