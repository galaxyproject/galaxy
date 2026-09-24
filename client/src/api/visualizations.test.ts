import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import { loadVisualizations, type VisualizationSummary } from "./visualizations";

const { server, http } = useServerMock();

function mockVisualization(id: string, title: string): VisualizationSummary {
    return {
        id,
        title,
        type: "nvd3_bar",
        annotation: null,
        create_time: "2026-01-01T00:00:00",
        update_time: "2026-01-02T00:00:00",
        deleted: false,
        importable: false,
        published: false,
        tags: [],
        username: "test-user",
    } as VisualizationSummary;
}

/** Captures the query parameters of the last intercepted index request. */
function interceptIndex(visualizations: VisualizationSummary[], totalMatches = "0") {
    const queries: Record<string, string>[] = [];

    server.use(
        http.get("/api/visualizations", ({ request, response }) => {
            const url = new URL(request.url);
            queries.push(Object.fromEntries(url.searchParams.entries()));
            return response(200).json(visualizations, { headers: { total_matches: totalMatches } });
        }),
    );

    return queries;
}

describe("loadVisualizations", () => {
    it("requests own visualizations and returns the total matches header", async () => {
        const expected = [mockVisualization("viz-1", "First"), mockVisualization("viz-2", "Second")];
        const queries = interceptIndex(expected, "17");

        const result = await loadVisualizations();

        expect(result.data).toEqual(expected);
        expect(result.totalMatches).toBe(17);
        expect(queries[0]).toMatchObject({
            limit: "24",
            offset: "0",
            search: "",
            sort_by: "update_time",
            sort_desc: "true",
            show_own: "true",
            show_published: "false",
            show_shared: "false",
        });
    });

    it("passes the explicit scope triplet and paging options through", async () => {
        const queries = interceptIndex([]);

        await loadVisualizations({
            showOwn: false,
            showShared: true,
            showPublished: true,
            search: "atac",
            sortBy: "title",
            sortDesc: false,
            limit: 5,
            offset: 10,
        });

        expect(queries[0]).toMatchObject({
            limit: "5",
            offset: "10",
            search: "atac",
            sort_by: "title",
            sort_desc: "false",
            show_own: "false",
            show_published: "true",
            show_shared: "true",
        });
    });

    it("defaults the total matches to zero when the header is missing", async () => {
        server.use(
            http.get("/api/visualizations", ({ response }) => {
                return response(200).json([]);
            }),
        );

        const result = await loadVisualizations();

        expect(result.data).toEqual([]);
        expect(result.totalMatches).toBe(0);
    });

    it("throws on server errors", async () => {
        server.use(
            http.get("/api/visualizations", ({ response }) => {
                return response("4XX").json({ err_code: 400, err_msg: "Bad request" }, { status: 400 });
            }),
        );

        await expect(loadVisualizations()).rejects.toThrow();
    });
});
