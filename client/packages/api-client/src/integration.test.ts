import { afterEach, beforeEach, describe, expect, it, type MockInstance, vi } from "vitest";

import type { HistorySummary, MessageException } from "./api-types";
import { createGalaxyApi, GalaxyApi } from "./index";

const histories: HistorySummary[] = [
    {
        id: "1",
        name: "Test History 1",
        deleted: false,
        purged: false,
        archived: false,
        annotation: null,
        count: 0,
        published: false,
        update_time: "2026-01-01T00:00:00.000Z",
        tags: [],
        model_class: "History",
        url: "/api/histories/1",
    },
    {
        id: "2",
        name: "Test History 2",
        deleted: false,
        purged: false,
        archived: false,
        annotation: null,
        count: 0,
        published: false,
        update_time: "2026-01-01T00:00:00.000Z",
        tags: ["test"],
        model_class: "History",
        url: "/api/histories/2",
    },
];

describe("Galaxy API integration", () => {
    let fetchMock: MockInstance<typeof fetch>;

    beforeEach(() => {
        fetchMock = vi.spyOn(globalThis, "fetch");
        fetchMock.mockRejectedValue(new Error("No response configured for this request"));
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("exports the createGalaxyApi factory", () => {
        expect(typeof createGalaxyApi).toBe("function");
    });

    it("creates a working client through the backward-compatible GalaxyApi factory", async () => {
        fetchMock.mockResolvedValue(Response.json(histories));

        expect(typeof GalaxyApi).toBe("function");
        const api = GalaxyApi();
        expect(typeof api.GET).toBe("function");

        const { data } = await api.GET("/api/histories");
        expect(data).toEqual(histories);
        expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
            expect.objectContaining({ url: `${window.location.origin}/api/histories`, method: "GET" }),
            undefined,
        );
    });

    it("retrieves and parses typed history summaries", async () => {
        fetchMock.mockResolvedValue(Response.json(histories));
        const api = createGalaxyApi();

        const { data, error } = await api.GET("/api/histories");

        expect(error).toBeUndefined();
        expect(data).toEqual(histories);
        expect(data?.[0]?.id).toBe("1");
        expect(data?.[0]?.name).toBe("Test History 1");
        expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
            expect.objectContaining({ url: `${window.location.origin}/api/histories`, method: "GET" }),
            undefined,
        );
    });

    it("substitutes the requested history ID in the endpoint path", async () => {
        fetchMock.mockResolvedValue(Response.json(histories[0]));
        const api = createGalaxyApi();

        const { data, error } = await api.GET("/api/histories/{history_id}", {
            params: { path: { history_id: "1" } },
        });

        expect(error).toBeUndefined();
        expect(data).toEqual(histories[0]);
        expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
            expect.objectContaining({ url: `${window.location.origin}/api/histories/1`, method: "GET" }),
            undefined,
        );
    });

    it("returns the server error when a requested history does not exist", async () => {
        const notFound = {
            err_code: 404,
            err_msg: "Not found",
        } satisfies MessageException;
        fetchMock.mockResolvedValue(Response.json(notFound, { status: 404 }));
        const api = createGalaxyApi();

        const { data, error, response } = await api.GET("/api/histories/{history_id}", {
            params: { path: { history_id: "missing-history" } },
        });

        expect(data).toBeUndefined();
        expect(error).toEqual(notFound);
        expect(response.status).toBe(404);
        expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
            expect.objectContaining({ url: `${window.location.origin}/api/histories/missing-history`, method: "GET" }),
            undefined,
        );
    });
});
