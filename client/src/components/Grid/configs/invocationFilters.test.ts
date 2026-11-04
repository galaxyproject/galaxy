import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import { NAME_MATCH_LIMIT, nameSearch, resolveInvocationFilters } from "./invocationFilters";

const { server, http } = useServerMock();

const workflowQueries = vi.fn();
const historyQueries = vi.fn();

type Listing = Record<string, Array<{ id: string; name: string }>>;

/** Serve each listing keyed by the request's `search` (plus `+hidden` for hidden workflows) */
function mockIndexes(workflows: Listing, histories: Listing, totals: Record<string, number> = {}) {
    server.use(
        http.get("/api/workflows", ({ request, response }) => {
            const query = Object.fromEntries(new URL(request.url).searchParams);
            workflowQueries(query);
            const key = query.show_hidden === "true" ? `${query.search}+hidden` : query.search!;
            const items = workflows[key] ?? [];
            const total = String(totals[key] ?? items.length);
            return response.untyped(HttpResponse.json(items, { headers: { total_matches: total } }));
        }),
        http.get("/api/histories", ({ request, response }) => {
            const query = Object.fromEntries(new URL(request.url).searchParams);
            historyQueries(query);
            const items = histories[query.search!] ?? [];
            const total = String(totals[query.search!] ?? items.length);
            return response.untyped(HttpResponse.json(items, { headers: { total_matches: total } }));
        }),
    );
}

describe("nameSearch", () => {
    it.each([
        ["rna", "name:rna"],
        ["rna seq", "name:rna name:seq"],
        ["'RNA seq'", "name:'RNA seq'"],
    ])("turns %j into %j", (value, expected) => {
        expect(nameSearch(value)).toBe(expected);
    });
});

describe("resolveInvocationFilters", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        workflowQueries.mockReset();
        historyQueries.mockReset();
    });

    it("passes id filters through without lookups", async () => {
        mockIndexes({}, {});

        const resolved = await resolveInvocationFilters("workflow_id:f2db41e1fa331b3e history_id:1cd8e2f6b131e891");

        expect(resolved).toEqual({
            params: { workflow_id: ["f2db41e1fa331b3e"], history_id: ["1cd8e2f6b131e891"] },
            matches: {},
        });
        expect(workflowQueries).not.toHaveBeenCalled();
        expect(historyQueries).not.toHaveBeenCalled();
    });

    it("looks up visible, deleted and hidden workflows by name", async () => {
        mockIndexes(
            {
                "name:rna": [{ id: "visible", name: "RNA-seq" }],
                "name:rna is:deleted": [{ id: "deleted", name: "old RNA-seq" }],
                "name:rna+hidden": [
                    { id: "hidden", name: "RNA-seq (hidden)" },
                    { id: "visible", name: "RNA-seq" },
                ],
            },
            {},
        );

        const resolved = await resolveInvocationFilters("rna");

        expect(resolved.params).toEqual({ workflow_id: ["visible", "deleted", "hidden"] });
        expect(resolved.matches.workflows).toMatchObject({ search: "rna", truncated: false });
        expect(resolved.matches.workflows!.items.map((workflow) => workflow.id)).toEqual([
            "visible",
            "deleted",
            "hidden",
        ]);
        expect(workflowQueries).toHaveBeenCalledWith(
            expect.objectContaining({ search: "name:rna", show_published: "true" }),
        );
        expect(workflowQueries).toHaveBeenCalledWith(expect.objectContaining({ search: "name:rna is:deleted" }));
        expect(workflowQueries).toHaveBeenCalledWith(
            expect.objectContaining({ search: "name:rna", show_hidden: "true" }),
        );
    });

    it("looks up active, deleted and purged histories by exact name", async () => {
        mockIndexes(
            {},
            {
                "name:'My data'": [{ id: "active", name: "My data" }],
                "name:'My data' is:deleted": [],
                "name:'My data' is:purged": [{ id: "purged", name: "My data" }],
            },
        );

        const resolved = await resolveInvocationFilters("history:'My data'");

        expect(resolved.params).toEqual({ history_id: ["active", "purged"] });
        expect(resolved.matches.histories!.search).toBe("'My data'");
        expect(historyQueries).toHaveBeenCalledWith(
            expect.objectContaining({ search: "name:'My data'", show_archived: "true", show_own: "true" }),
        );
    });

    it("returns no parameters when a name matches nothing", async () => {
        mockIndexes({}, { "name:results": [{ id: "history-1", name: "results" }] });

        const resolved = await resolveInvocationFilters("workflow:missing history:results");

        expect(resolved.params).toBeNull();
        expect(resolved.matches.workflows!.items).toEqual([]);
        expect(resolved.matches.histories!.items).toHaveLength(1);
    });

    it("prefers an id filter over a name filter for the same kind", async () => {
        mockIndexes({}, {});

        const resolved = await resolveInvocationFilters("workflow:rna workflow_id:f2db41e1fa331b3e");

        expect(resolved.params).toEqual({ workflow_id: ["f2db41e1fa331b3e"] });
        expect(workflowQueries).not.toHaveBeenCalled();
    });

    it("flags matches beyond the lookup limit", async () => {
        mockIndexes({ "name:a": [{ id: "workflow-1", name: "a" }] }, {}, { "name:a": NAME_MATCH_LIMIT + 1 });

        const resolved = await resolveInvocationFilters("workflow:a");

        expect(resolved.matches.workflows!.truncated).toBe(true);
    });
});
