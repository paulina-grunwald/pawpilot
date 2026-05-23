import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { DeletePetDialog } from "./DeletePetDialog";
import { getApiBaseUrl } from "@/lib/auth";

const replaceSpy = vi.fn();
const refreshSpy = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceSpy, refresh: refreshSpy }),
}));

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  replaceSpy.mockClear();
  refreshSpy.mockClear();
});
afterAll(() => server.close());

describe("DeletePetDialog", () => {
  it("does not render anything when open is false", () => {
    const { container } = render(
      <DeletePetDialog open={false} petId="pet-1" petName="Luna" onClose={() => {}} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("disables the delete button until the confirmation matches the pet name", async () => {
    const user = userEvent.setup();
    render(<DeletePetDialog open petId="pet-1" petName="Luna" onClose={() => {}} />);
    const deleteButton = screen.getByRole("button", { name: /delete forever/i });
    expect(deleteButton).toBeDisabled();

    const input = screen.getByRole("textbox");
    await user.type(input, "luma");
    expect(deleteButton).toBeDisabled();
    await user.clear(input);
    await user.type(input, "Luna");
    expect(deleteButton).toBeEnabled();
  });

  it("matches confirmation case-insensitively", async () => {
    const user = userEvent.setup();
    render(<DeletePetDialog open petId="pet-1" petName="Luna" onClose={() => {}} />);
    await user.type(screen.getByRole("textbox"), "lUnA");
    expect(screen.getByRole("button", { name: /delete forever/i })).toBeEnabled();
  });

  it("calls DELETE /pets/{id} and redirects to /dashboard on 204", async () => {
    let called = false;
    server.use(
      http.delete(`${getApiBaseUrl()}/pets/pet-1`, () => {
        called = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    render(<DeletePetDialog open petId="pet-1" petName="Luna" onClose={() => {}} />);
    await user.type(screen.getByRole("textbox"), "Luna");
    await user.click(screen.getByRole("button", { name: /delete forever/i }));
    await waitFor(() => expect(called).toBe(true));
    await waitFor(() => expect(replaceSpy).toHaveBeenCalledWith("/dashboard"));
    expect(refreshSpy).toHaveBeenCalled();
  });

  it("surfaces a friendly error and stays open on failure", async () => {
    server.use(
      http.delete(`${getApiBaseUrl()}/pets/pet-1`, () =>
        HttpResponse.json({ detail: "Boom" }, { status: 500 }),
      ),
    );
    const user = userEvent.setup();
    render(<DeletePetDialog open petId="pet-1" petName="Luna" onClose={() => {}} />);
    await user.type(screen.getByRole("textbox"), "Luna");
    await user.click(screen.getByRole("button", { name: /delete forever/i }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/couldn't delete/i),
    );
    expect(replaceSpy).not.toHaveBeenCalled();
  });

  it("calls onClose when the Cancel button is clicked", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<DeletePetDialog open petId="pet-1" petName="Luna" onClose={onClose} />);
    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when Escape is pressed", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<DeletePetDialog open petId="pet-1" petName="Luna" onClose={onClose} />);
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });
});
