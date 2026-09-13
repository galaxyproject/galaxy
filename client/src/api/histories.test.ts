import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import {
    getArchivedHistories,
    getHistories,
    getMyHistories,
    getPublishedHistories,
    getSharedHistories,
    type MyHistory,
} from "./histories";

const { server, http } = useServerMock();

function mockHistory(id: string, name: string): MyHistory {
    return {
        id,
        name,
        model_class: "History",
        annotation: null,
        archived: false,
        count: 0,
        deleted: false,
        published: false,
        purged: false,
        tags: [],
        update_time: "2026-01-02T00:00:00",
        username: "test-user",
    } as unknown as MyHistory;
}

/** Captures the query parameters of the intercepted history index requests. */
function interceptIndex(path: "/api/histories" | "/api/histories/archived", histories: unknown[], totalMatches = "0") {
    const queries: Record<string, string>[] = [];

    server.use(
        http.get(path, ({ request, response }) => {
            const url = new URL(request.url);
            queries.push(Object.fromEntries(url.searchParams.entries()));
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return response(200).json(histories as any, { headers: { total_matches: totalMatches } });
        }),
    );

    return queries;
}

describe("getMyHistories", () => {
    it("returns the histories and the total matches header", async () => {
        const expected = [mockHistory("h1", "First"), mockHistory("h2", "Second")];
        interceptIndex("/api/histories", expected, "42");

        const result = await getMyHistories();

        expect(result.data).toEqual(expected);
        expect(result.total).toBe(42);
    });

    it("never requests published histories, so a user listing cannot leak public ones", async () => {
        const queries = interceptIndex("/api/histories", []);

        await getMyHistories();

        expect(queries[0]).toMatchObject({
            view: "summary",
            keys: "username",
            limit: "24",
            offset: "0",
            search: "",
            sort_by: "update_time",
            sort_desc: "false",
            show_own: "true",
            show_published: "false",
            show_shared: "false",
            show_archived: "false",
        });
    });

    it("forwards pagination, search and sorting options", async () => {
        const queries = interceptIndex("/api/histories", []);

        await getMyHistories({ limit: 5, offset: 10, search: "rna", sortBy: "name", sortDesc: true });

        expect(queries[0]).toMatchObject({
            limit: "5",
            offset: "10",
            search: "rna",
            sort_by: "name",
            sort_desc: "true",
            show_own: "true",
            show_published: "false",
        });
    });
});

describe("getSharedHistories", () => {
    it("requests only histories shared with the current user", async () => {
        const queries = interceptIndex("/api/histories", []);

        await getSharedHistories({ search: "shared" });

        expect(queries[0]).toMatchObject({
            keys: "username,owner",
            search: "shared",
            show_own: "false",
            show_published: "false",
            show_shared: "true",
            show_archived: "false",
        });
    });
});

describe("getPublishedHistories", () => {
    it("requests only published histories", async () => {
        const queries = interceptIndex("/api/histories", []);

        await getPublishedHistories();

        expect(queries[0]).toMatchObject({
            keys: "username,owner,published",
            show_own: "false",
            show_published: "true",
            show_shared: "false",
            show_archived: "false",
        });
    });
});

describe("getArchivedHistories", () => {
    it("uses the archived endpoint and forwards the listing options", async () => {
        const expected = [mockHistory("h3", "Archived")];
        const queries = interceptIndex("/api/histories/archived", expected, "3");

        const result = await getArchivedHistories({ limit: 7, search: "old" });

        expect(result.data).toEqual(expected);
        expect(result.total).toBe(3);
        expect(queries[0]).toMatchObject({
            view: "summary",
            limit: "7",
            offset: "0",
            search: "old",
            sort_by: "update_time",
            sort_desc: "false",
        });
    });
});

describe("getHistories", () => {
    it("defaults to the current user's own, non-archived histories", async () => {
        const queries = interceptIndex("/api/histories", []);

        await getHistories();

        expect(queries[0]).toMatchObject({
            show_own: "true",
            show_published: "false",
            show_shared: "false",
            show_archived: "false",
        });
    });

    it("accepts explicit visibility flags", async () => {
        const queries = interceptIndex("/api/histories", []);

        await getHistories({ showOwn: false, showPublished: true, showShared: true, showArchived: true });

        expect(queries[0]).toMatchObject({
            show_own: "false",
            show_published: "true",
            show_shared: "true",
            show_archived: "true",
        });
    });
});
