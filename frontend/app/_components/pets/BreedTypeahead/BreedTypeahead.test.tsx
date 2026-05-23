import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { useState } from "react";
import { BreedTypeahead } from "./BreedTypeahead";
import { getApiBaseUrl } from "@/lib/auth";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const AUSSIE_BREEDS = [
  { name: "Australian Cattle Dog", group: "Herding", size_category: "medium" },
  { name: "Australian Shepherd", group: "Herding", size_category: "medium" },
  { name: "Australian Terrier", group: "Terrier", size_category: "small" },
];

function ControlledHarness({ initial = "" }: { initial?: string }) {
  const [value, setValue] = useState(initial);
  return <BreedTypeahead value={value} onChange={setValue} />;
}

describe("BreedTypeahead", () => {
  it("opens the listbox on focus and queries /breeds", async () => {
    let calledOnce = false;
    server.use(
      http.get(`${getApiBaseUrl()}/breeds`, () => {
        calledOnce = true;
        return HttpResponse.json(AUSSIE_BREEDS);
      }),
    );
    const user = userEvent.setup();
    render(<ControlledHarness />);

    await user.click(screen.getByRole("combobox"));
    await waitFor(() => expect(calledOnce).toBe(true));
    expect(screen.getByRole("listbox")).toBeInTheDocument();
  });

  it("debounces typing and surfaces the latest matches", async () => {
    server.use(
      http.get(`${getApiBaseUrl()}/breeds`, ({ request }) => {
        const query = new URL(request.url).searchParams.get("q") ?? "";
        const filtered = AUSSIE_BREEDS.filter((breed) =>
          breed.name.toLowerCase().includes(query.toLowerCase()),
        );
        return HttpResponse.json(filtered);
      }),
    );
    const user = userEvent.setup();
    render(<ControlledHarness />);

    const combobox = screen.getByRole("combobox");
    await user.click(combobox);
    await user.type(combobox, "aus");

    await waitFor(() => {
      expect(
        screen.getByRole("option", { name: /australian shepherd/i }),
      ).toBeInTheDocument();
    });
  });

  it("selecting an option populates the input and closes the listbox", async () => {
    server.use(
      http.get(`${getApiBaseUrl()}/breeds`, () => HttpResponse.json(AUSSIE_BREEDS)),
    );
    const user = userEvent.setup();
    render(<ControlledHarness />);

    await user.click(screen.getByRole("combobox"));
    const option = await screen.findByRole("option", { name: /australian shepherd/i });
    await user.click(option);

    expect(screen.getByRole("combobox")).toHaveValue("Australian Shepherd");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("closes the listbox when Escape is pressed", async () => {
    server.use(
      http.get(`${getApiBaseUrl()}/breeds`, () => HttpResponse.json(AUSSIE_BREEDS)),
    );
    const user = userEvent.setup();
    render(<ControlledHarness />);

    await user.click(screen.getByRole("combobox"));
    await screen.findByRole("listbox");
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("keeps the user's typed value when the network call fails", async () => {
    server.use(
      http.get(`${getApiBaseUrl()}/breeds`, () => HttpResponse.error()),
    );
    const user = userEvent.setup();
    render(<ControlledHarness />);

    await user.type(screen.getByRole("combobox"), "Mutt");
    expect(screen.getByRole("combobox")).toHaveValue("Mutt");
  });

  it("shows a helpful empty state when no results match a non-empty query", async () => {
    server.use(
      http.get(`${getApiBaseUrl()}/breeds`, () => HttpResponse.json([])),
    );
    const user = userEvent.setup();
    render(<ControlledHarness />);
    await user.type(screen.getByRole("combobox"), "zzz");
    await waitFor(() =>
      expect(screen.getByText(/no matches/i)).toBeInTheDocument(),
    );
  });
});

vi.useRealTimers();
