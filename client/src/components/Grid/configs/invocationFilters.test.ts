import { getFakeRegisteredUser } from "@tests/test-data";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useUserStore } from "@/stores/userStore";

import {
    historyColumnFilter,
    invocationSearch,
    invocationsFiltering,
    NAME_MATCH_LIMIT,
    nameSearch,
    RECENT_LIMIT,
    workflowColumnFilter,
} from "./invocationFilters";

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

    it("uses the given key", () => {
        expect(nameSearch("rna seq", "workflow")).toBe("workflow:rna workflow:seq");
        expect(nameSearch("'My data'", "history")).toBe("history:'My data'");
    });
});

describe("invocationSearch", () => {
    it.each([
        ["", undefined],
        ["rna", "workflow:rna"],
        ["workflow:rna", "workflow:rna"],
        ["history:'My data'", "history:'My data'"],
        ["workflow:rna history:batch", "workflow:rna history:batch"],
        [
            "workflow_id:f2db41e1fa331b3e workflow_id:a7db2fac67043c7e",
            "workflow_id:f2db41e1fa331b3e workflow_id:a7db2fac67043c7e",
        ],
        ["history_id:1cd8e2f6b131e891", "history_id:1cd8e2f6b131e891"],
        ["workflow_id:f2db41e1fa331b3e workflow:rna", "workflow:rna workflow_id:f2db41e1fa331b3e"],
    ])("turns %j into the search %j", (text, search) => {
        expect(invocationSearch(text)).toBe(search);
    });

    it("keeps a quoted name with a colon in one term", () => {
        expect(invocationSearch("workflow:'Foo bar: baz'")).toBe("workflow:'Foo bar: baz'");
        expect(
            Object.fromEntries(
                invocationsFiltering.getFiltersForText("workflow:'Foo bar: baz' history:x", true, false),
            ),
        ).toEqual({ workflow: "'Foo bar: baz'", history: "x" });
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

    it("looks up visible, deleted and hidden workflows by name", async () => {
        mockIndexes(
            {
                "name:rna": [{ id: "visible", name: "RNA-seq", owner: "me" }],
                "name:rna is:deleted": [{ id: "deleted", name: "old RNA-seq", owner: "me" }],
                "name:rna+hidden": [
                    { id: "hidden", name: "RNA-seq (hidden)", owner: "me" },
                    { id: "visible", name: "RNA-seq", owner: "me" },
                ],
            },
            {},
        );

        const options = await workflowColumnFilter.search("rna");

        expect(options.map((option) => option.id)).toEqual(["visible", "deleted", "hidden"]);
        expect(workflowQueries).toHaveBeenCalledWith(
            expect.objectContaining({ search: "name:rna", show_published: "true" }),
        );
        expect(workflowQueries).toHaveBeenCalledWith(expect.objectContaining({ search: "name:rna is:deleted" }));
        expect(workflowQueries).toHaveBeenCalledWith(
            expect.objectContaining({ search: "name:rna", show_hidden: "true" }),
        );
    });

    it("keeps the user's own workflows when published ones fill the match limit", async () => {
        const published = Array.from({ length: NAME_MATCH_LIMIT }, (_, index) => ({
            id: `published-${index}`,
            owner: "alice",
        }));
        server.use(
            http.get("/api/workflows", ({ request, response }) => {
                const query = new URL(request.url).searchParams;
                const visible = query.get("search") === "name:rna" && query.get("show_hidden") !== "true";
                const own = [{ id: "own", owner: "me" }];
                const items = !visible ? [] : query.get("show_published") === "true" ? published : own;
                return response.untyped(HttpResponse.json(items, { headers: { total_matches: String(items.length) } }));
            }),
        );

        const options = await workflowColumnFilter.search("rna");

        expect(options.map((option) => option.id)).toContain("own");
    });

    it("looks up active, deleted and purged histories by exact name", async () => {
        mockIndexes(
            {},
            {
                "name:'My data'": [{ id: "active", name: "My data" }],
                "name:'My data' is:purged": [{ id: "purged", name: "My data" }],
            },
        );

        const options = await historyColumnFilter.search("'My data'");

        expect(options.map((option) => option.id)).toEqual(["active", "purged"]);
        expect(historyQueries).toHaveBeenCalledWith(
            expect.objectContaining({ search: "name:'My data'", show_archived: "true", show_own: "true" }),
        );
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
