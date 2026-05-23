import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { getApiBaseUrl } from "./auth";
import { searchBreeds } from "./breeds";

const API = getApiBaseUrl();

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("searchBreeds", () => {
  it("returns parsed breeds on success and forwards q + limit", async () => {
    let receivedQuery: string | null = null;
    let receivedLimit: string | null = null;
    server.use(
      http.get(`${API}/breeds`, ({ request }) => {
        const url = new URL(request.url);
        receivedQuery = url.searchParams.get("q");
        receivedLimit = url.searchParams.get("limit");
        return HttpResponse.json([
          { name: "Border Collie", group: "Herding", size_category: "medium" },
        ]);
      }),
    );

    const breeds = await searchBreeds("border", 5);
    expect(breeds).toHaveLength(1);
    expect(breeds[0].name).toBe("Border Collie");
    expect(receivedQuery).toBe("border");
    expect(receivedLimit).toBe("5");
  });

  it("omits the q param when query is empty", async () => {
    let hasQ = true;
    server.use(
      http.get(`${API}/breeds`, ({ request }) => {
        const url = new URL(request.url);
        hasQ = url.searchParams.has("q");
        return HttpResponse.json([]);
      }),
    );
    await searchBreeds("");
    expect(hasQ).toBe(false);
  });

  it("throws when the response is not ok", async () => {
    server.use(http.get(`${API}/breeds`, () => new HttpResponse(null, { status: 500 })));
    await expect(searchBreeds("foo")).rejects.toThrow(/500/);
  });
});
