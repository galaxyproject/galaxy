import { getFakeRegisteredUser } from "@tests/test-data";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useUserStore } from "@/stores/userStore";

import {
    historyColumnFilter,
    NAME_MATCH_LIMIT,
    NAME_MATCH_TTL_MS,
    nameSearch,
    RECENT_LIMIT,
    resolveInvocationFilters,
    workflowColumnFilter,
} from "./invocationFilters";
import invocationsGridConfig from "./invocations";

const { server, http } = useServerMock();

const workflowQueries = vi.fn();
const historyQueries = vi.fn();
const countRequests = vi.fn();

type Listing = Record<string, Array<Record<string, unknown>>>;

/** Serve each listing keyed by the request's `search` (plus `+hidden` for hidden workflows) */
function mockIndexes(workflows: Listing, histories: Listing) {
    server.use(
        http.get("/api/workflows", ({ request, response }) => {
            const query = Object.fromEntries(new URL(request.url).searchParams);
            workflowQueries(query);
            const search = query.search ?? "";
            const key = query.show_hidden === "true" ? `${search}+hidden` : search;
            const items = workflows[key] ?? [];
            return response.untyped(HttpResponse.json(items, { headers: { total_matches: String(items.length) } }));
        }),
        http.get("/api/histories", ({ request, response }) => {
            const query = Object.fromEntries(new URL(request.url).searchParams);
            historyQueries(query);
            const items = histories[query.search ?? ""] ?? [];
            return response.untyped(HttpResponse.json(items, { headers: { total_matches: String(items.length) } }));
        }),
        http.get("/api/workflows/{workflow_id}/counts", ({ params, response }) => {
            countRequests(params.workflow_id);
            return response(200).json(params.workflow_id === "visible" ? { scheduled: 2 } : { scheduled: 1 });
        }),
    );
}

describe("module loading", () => {
    it("wires the column filters into the grid when this module loads first", () => {
        const filters = invocationsGridConfig.fields.map((field) => field.filter).filter(Boolean);
        expect(filters).toEqual([workflowColumnFilter, historyColumnFilter]);
    });
});

describe("nameSearch", () => {
    it.each([
        ["rna", "name:rna"],
        ["rna seq", "name:rna name:seq"],
        ["'RNA seq'", "name:'RNA seq'"],
        ["RNA-seq (PE)", "name:RNA-seq name:PE"],
        ["VGP v1.2", "name:VGP name:v1 name:2"],
        ["#1", "name:1"],
        ["++", "name:'++'"],
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

    it("passes picked ids through without lookups", async () => {
        mockIndexes({}, {});

        const params = await resolveInvocationFilters(
            "workflow_id:f2db41e1fa331b3e,a7db2fac67043c7e history_id:1cd8e2f6b131e891",
        );

        expect(params).toEqual({
            workflow_id: ["f2db41e1fa331b3e", "a7db2fac67043c7e"],
            history_id: ["1cd8e2f6b131e891"],
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

        const params = await resolveInvocationFilters("rna");

        expect(params).toEqual({ workflow_id: ["visible", "deleted", "hidden"] });
        expect(workflowQueries).toHaveBeenCalledWith(
            expect.objectContaining({ search: "name:rna", show_published: "true" }),
        );
        expect(workflowQueries).toHaveBeenCalledWith(expect.objectContaining({ search: "name:rna is:deleted" }));
        expect(workflowQueries).toHaveBeenCalledWith(
            expect.objectContaining({ search: "name:rna", show_hidden: "true" }),
        );
    });

    it("keeps the user's own workflows when published ones fill the match limit", async () => {
        const published = Array.from({ length: NAME_MATCH_LIMIT }, (_, index) => ({ id: `published-${index}` }));
        server.use(
            http.get("/api/workflows", ({ request, response }) => {
                const query = new URL(request.url).searchParams;
                const visible = query.get("search") === "name:rna" && query.get("show_hidden") !== "true";
                const items = !visible ? [] : query.get("show_published") === "true" ? published : [{ id: "own" }];
                return response.untyped(HttpResponse.json(items, { headers: { total_matches: String(items.length) } }));
            }),
        );

        const params = await resolveInvocationFilters("workflow:rna");

        expect(params?.workflow_id).toContain("own");
    });

    it("looks up active, deleted and purged histories by exact name", async () => {
        mockIndexes(
            {},
            {
                "name:'My data'": [{ id: "active", name: "My data" }],
                "name:'My data' is:purged": [{ id: "purged", name: "My data" }],
            },
        );

        const params = await resolveInvocationFilters("history:'My data'");

        expect(params).toEqual({ history_id: ["active", "purged"] });
        expect(historyQueries).toHaveBeenCalledWith(
            expect.objectContaining({ search: "name:'My data'", show_archived: "true", show_own: "true" }),
        );
    });

    it("repeats name lookups only when the text changes or the last ones are old", async () => {
        mockIndexes({ "name:paging": [{ id: "visible", name: "paging" }] }, {});
        const now = vi.spyOn(Date, "now").mockReturnValue(1_000_000);

        const first = await resolveInvocationFilters("workflow:paging");
        const lookups = workflowQueries.mock.calls.length;
        expect(await resolveInvocationFilters("workflow:paging")).toEqual(first);
        expect(workflowQueries).toHaveBeenCalledTimes(lookups);

        await resolveInvocationFilters("workflow:other");
        await resolveInvocationFilters("workflow:paging");
        expect(workflowQueries).toHaveBeenCalledTimes(3 * lookups);

        now.mockReturnValue(1_000_000 + NAME_MATCH_TTL_MS);
        await resolveInvocationFilters("workflow:paging");
        expect(workflowQueries).toHaveBeenCalledTimes(4 * lookups);
        now.mockRestore();
    });

    it("returns null when a name matches nothing", async () => {
        mockIndexes({}, { "name:results": [{ id: "history-1", name: "results" }] });

        expect(await resolveInvocationFilters("workflow:missing history:results")).toBeNull();
    });

    it("narrows picked ids to the ones matching a name filter", async () => {
        mockIndexes({ "name:rna": [{ id: "visible", name: "RNA-seq" }] }, {});

        expect(await resolveInvocationFilters("workflow:rna workflow_id:visible,other")).toEqual({
            workflow_id: ["visible"],
        });
        expect(await resolveInvocationFilters("workflow:rna workflow_id:other")).toBeNull();
    });
});

describe("column filters", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        useUserStore().currentUser = getFakeRegisteredUser({ username: "me" });
        workflowQueries.mockReset();
        historyQueries.mockReset();
        countRequests.mockReset();
    });

    it("lists the most recently updated own workflows before anything is typed", async () => {
        mockIndexes({ "": [{ id: "visible", name: "RNA-seq", owner: "me", update_time: "2026-11-01T10:00:00" }] }, {});

        const options = await workflowColumnFilter.search("");

        expect(workflowQueries).toHaveBeenCalledTimes(1);
        expect(workflowQueries).toHaveBeenCalledWith(
            expect.objectContaining({ limit: String(RECENT_LIMIT), sort_by: "update_time", sort_desc: "true" }),
        );
        expect(options.map(({ id, name, updateTime }) => ({ id, name, updateTime }))).toEqual([
            { id: "visible", name: "RNA-seq", updateTime: "2026-11-01T10:00:00" },
        ]);
    });

    it("describes workflows by run count, owner and state", async () => {
        mockIndexes(
            {
                "name:rna": [{ id: "visible", name: "RNA-seq", owner: "me" }],
                "name:rna is:deleted": [{ id: "deleted", name: "RNA-seq", owner: "alice", deleted: true }],
            },
            {},
        );

        const options = await workflowColumnFilter.search("rna");
        options.forEach((option) => option.detail?.());
        await flushPromises();

        expect(options.map((option) => option.detail?.())).toEqual(["2 runs", "by alice · deleted"]);
        expect(countRequests.mock.calls).toEqual([["visible"]]);
    });

    it("describes histories by item count and state", async () => {
        mockIndexes(
            {},
            {
                "name:batch": [{ id: "active", name: "batch 1", count: 3 }],
                "name:batch is:deleted": [{ id: "deleted", name: "batch 2", count: 1, deleted: true }],
            },
        );

        const options = await historyColumnFilter.search("batch");

        expect(options.map((option) => [option.name, option.detail?.()])).toEqual([
            ["batch 1", "3 items"],
            ["batch 2", "1 item · deleted"],
        ]);
    });

    it("marks hidden workflows", async () => {
        mockIndexes({ "name:rna+hidden": [{ id: "hidden", name: "RNA-seq", owner: "alice", hidden: true }] }, {});

        const [option] = await workflowColumnFilter.search("rna");

        expect(option?.detail?.()).toBe("by alice · hidden");
    });

    it("marks a history with its most final state", async () => {
        mockIndexes(
            {},
            {
                "name:batch": [{ id: "archived", name: "batch", count: 1, archived: true }],
                "name:batch is:deleted": [{ id: "deleted", name: "batch", count: 1, deleted: true, archived: true }],
                "name:batch is:purged": [{ id: "purged", name: "batch", count: 1, purged: true, deleted: true }],
            },
        );

        const options = await historyColumnFilter.search("batch");

        expect(options.map((option) => option.detail?.())).toEqual([
            "1 item · archived",
            "1 item · deleted",
            "1 item · purged",
        ]);
    });

    it("lists the most recently updated histories before anything is typed", async () => {
        mockIndexes({}, { "": [{ id: "active", name: "batch", count: 2 }] });

        const options = await historyColumnFilter.search("");

        expect(historyQueries).toHaveBeenCalledTimes(1);
        expect(historyQueries).toHaveBeenCalledWith(
            expect.objectContaining({ limit: String(RECENT_LIMIT), sort_by: "update_time", sort_desc: "true" }),
        );
        expect(options.map((option) => option.id)).toEqual(["active"]);
    });
});
