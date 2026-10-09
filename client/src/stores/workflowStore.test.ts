import { getFakeWorkflowSummary } from "@tests/test-data/workflows";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { WorkflowSummary } from "@/api/workflows";
import { loadWorkflows } from "@/api/workflows";
import { getWorkflowFull } from "@/components/Workflow/workflows.services";
import { useWorkflowStore } from "@/stores/workflowStore";

import { setupTestPinia } from "./testUtils";

vi.mock("@/components/Workflow/workflows.services", () => ({
    getWorkflowFull: vi.fn(),
}));

vi.mock("@/api/workflows", () => ({
    loadWorkflows: vi.fn(),
}));

const mockWorkflow = {
    id: "workflow-123",
    name: "Test Workflow",
    version: 1,
    steps: {},
};

function workflowSummary(id: string, name: string, extra: Partial<WorkflowSummary> = {}): WorkflowSummary {
    return getFakeWorkflowSummary({ id, name, ...extra });
}

function deferred<T>() {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((resolvePromise) => {
        resolve = resolvePromise;
    });
    return { promise, resolve };
}

function mockLoadWorkflowsOnce(data: WorkflowSummary[]) {
    vi.mocked(loadWorkflows).mockResolvedValueOnce({ data, totalMatches: data.length });
}

describe("useWorkflowStore", () => {
    let workflowStore: ReturnType<typeof useWorkflowStore>;

    beforeEach(() => {
        setupTestPinia();
        workflowStore = useWorkflowStore();
        vi.mocked(getWorkflowFull).mockReset();
        vi.mocked(loadWorkflows).mockReset();
    });

    describe("getFullWorkflowCached", () => {
        it("fetches an uncached workflow and version", async () => {
            vi.mocked(getWorkflowFull).mockResolvedValue(mockWorkflow);

            const result = await workflowStore.getFullWorkflowCached("workflow-123", 1);

            expect(getWorkflowFull).toHaveBeenCalledTimes(1);
            expect(getWorkflowFull).toHaveBeenCalledWith("workflow-123", 1);
            expect(result).toEqual(mockWorkflow);
        });

        it("returns a cached workflow without another request", async () => {
            vi.mocked(getWorkflowFull).mockResolvedValue(mockWorkflow);

            const firstResult = await workflowStore.getFullWorkflowCached("workflow-123", 1);
            expect(getWorkflowFull).toHaveBeenCalledTimes(1);
            expect(firstResult).toEqual(mockWorkflow);

            const secondResult = await workflowStore.getFullWorkflowCached("workflow-123", 1);

            expect(getWorkflowFull).toHaveBeenCalledTimes(1);
            expect(secondResult).toEqual(mockWorkflow);
        });

        it.each([2, 5])(
            "deduplicates %i concurrent requests for the same workflow and version",
            async (requestCount) => {
                const response = deferred<typeof mockWorkflow>();
                vi.mocked(getWorkflowFull).mockReturnValue(response.promise);

                const requests = Array.from({ length: requestCount }, () =>
                    workflowStore.getFullWorkflowCached("workflow-123", 1),
                );

                expect(getWorkflowFull).toHaveBeenCalledTimes(1);
                response.resolve(mockWorkflow);
                expect(await Promise.all(requests)).toEqual(Array(requestCount).fill(mockWorkflow));
                expect(getWorkflowFull).toHaveBeenCalledTimes(1);
            },
        );

        it("fetches different workflows independently", async () => {
            const mockWorkflow1 = { ...mockWorkflow, id: "workflow-1" };
            const mockWorkflow2 = { ...mockWorkflow, id: "workflow-2" };

            vi.mocked(getWorkflowFull).mockResolvedValueOnce(mockWorkflow1);
            vi.mocked(getWorkflowFull).mockResolvedValueOnce(mockWorkflow2);

            const [firstResult, secondResult] = await Promise.all([
                workflowStore.getFullWorkflowCached("workflow-1"),
                workflowStore.getFullWorkflowCached("workflow-2"),
            ]);

            expect(getWorkflowFull).toHaveBeenCalledTimes(2);
            expect(firstResult).toEqual(mockWorkflow1);
            expect(secondResult).toEqual(mockWorkflow2);
        });

        it("fetches different versions of the same workflow independently", async () => {
            const mockWorkflowV1 = { ...mockWorkflow, version: 1 };
            const mockWorkflowV2 = { ...mockWorkflow, version: 2 };

            vi.mocked(getWorkflowFull).mockResolvedValueOnce(mockWorkflowV1);
            vi.mocked(getWorkflowFull).mockResolvedValueOnce(mockWorkflowV2);

            const [firstResult, secondResult] = await Promise.all([
                workflowStore.getFullWorkflowCached("workflow-123", 1),
                workflowStore.getFullWorkflowCached("workflow-123", 2),
            ]);

            expect(getWorkflowFull).toHaveBeenCalledTimes(2);
            expect(firstResult).toEqual(mockWorkflowV1);
            expect(secondResult).toEqual(mockWorkflowV2);
        });
    });

    describe("fetchWorkflowList", () => {
        it("requests the params of the 'my' variant and caches the returned summaries", async () => {
            const summaries = [workflowSummary("w1", "First"), workflowSummary("w2", "Second")];
            mockLoadWorkflowsOnce(summaries);

            const result = await workflowStore.fetchWorkflowList("my");

            expect(loadWorkflows).toHaveBeenCalledWith({
                sortBy: "update_time",
                sortDesc: true,
                limit: 20,
                offset: 0,
                filterText: "",
                showPublished: false,
                // explicit `false`, so the request does not fall back to the
                // backend default (which includes shared-with-me workflows)
                showShared: false,
                skipStepCounts: true,
            });
            expect(result).toEqual(summaries);
            expect(workflowStore.getWorkflowList("my")).toEqual(summaries);
            expect(workflowStore.getWorkflowSummaryById("w1")).toEqual(summaries[0]);
        });

        it("requests shared workflows with show_shared and the shared filter", async () => {
            mockLoadWorkflowsOnce([workflowSummary("w3", "Shared")]);

            await workflowStore.fetchWorkflowList("shared", "rna");

            expect(loadWorkflows).toHaveBeenCalledWith(
                expect.objectContaining({
                    filterText: "rna is:shared_with_me",
                    showShared: true,
                    showPublished: false,
                }),
            );
        });

        it("requests published workflows with show_published and the published filter", async () => {
            mockLoadWorkflowsOnce([workflowSummary("w4", "Published")]);

            await workflowStore.fetchWorkflowList("published");

            expect(loadWorkflows).toHaveBeenCalledWith(
                expect.objectContaining({ filterText: "is:published", showPublished: true }),
            );
        });

        it("requests bookmarked workflows with the bookmarked filter", async () => {
            mockLoadWorkflowsOnce([workflowSummary("w5", "Bookmarked")]);

            await workflowStore.fetchWorkflowList("bookmarked");

            expect(loadWorkflows).toHaveBeenCalledWith(
                expect.objectContaining({ filterText: "is:bookmarked", showPublished: false, showShared: false }),
            );
        });

        it("applies sorting and paging overrides", async () => {
            mockLoadWorkflowsOnce([]);

            await workflowStore.fetchWorkflowList("my", "", { sortBy: "name", sortDesc: false, limit: 5, offset: 10 });

            expect(loadWorkflows).toHaveBeenCalledWith(
                expect.objectContaining({ sortBy: "name", sortDesc: false, limit: 5, offset: 10 }),
            );
        });

        it("merges updated summaries into the existing cache entry instead of duplicating it", async () => {
            mockLoadWorkflowsOnce([workflowSummary("w1", "Old name", { tags: ["a"] })]);
            await workflowStore.fetchWorkflowList("my");

            // A partial API summary must leave the cached tags intact.
            const updatedSummary: Partial<WorkflowSummary> = {
                id: "w1",
                name: "New name",
                update_time: "2026-08-31T10:00:00",
            };
            mockLoadWorkflowsOnce([updatedSummary as WorkflowSummary]);
            await workflowStore.fetchWorkflowList("published");

            expect(workflowStore.allWorkflowSummaries).toHaveLength(1);
            expect(workflowStore.getWorkflowSummaryById("w1")).toEqual(
                expect.objectContaining({ name: "New name", tags: ["a"] }),
            );
            // Both lists read the same cached summary
            expect(workflowStore.getWorkflowList("my")[0]).toEqual(workflowStore.getWorkflowList("published")[0]);
        });

        it("keeps separate ordered id lists per variant and query", async () => {
            mockLoadWorkflowsOnce([workflowSummary("w2", "Second"), workflowSummary("w1", "First")]);
            await workflowStore.fetchWorkflowList("my");

            mockLoadWorkflowsOnce([workflowSummary("w1", "First")]);
            await workflowStore.fetchWorkflowList("my", "first");

            expect(workflowStore.getWorkflowList("my").map((workflow) => workflow.id)).toEqual(["w2", "w1"]);
            expect(workflowStore.getWorkflowList("my", "first").map((workflow) => workflow.id)).toEqual(["w1"]);
            expect(workflowStore.getWorkflowList("shared")).toEqual([]);
        });

        it("deduplicates concurrent fetches of the same list", async () => {
            mockLoadWorkflowsOnce([workflowSummary("w1", "First")]);

            const [first, second] = await Promise.all([
                workflowStore.fetchWorkflowList("my"),
                workflowStore.fetchWorkflowList("my"),
            ]);

            expect(loadWorkflows).toHaveBeenCalledTimes(1);
            expect(first).toEqual(second);
        });

        it("keeps concurrent pages in separate request and cache slots", async () => {
            type WorkflowListResult = Awaited<ReturnType<typeof loadWorkflows>>;
            const page0Response = deferred<WorkflowListResult>();
            const page1Response = deferred<WorkflowListResult>();
            vi.mocked(loadWorkflows).mockImplementation(({ offset }) =>
                offset === 0 ? page0Response.promise : page1Response.promise,
            );
            const page0Options = { limit: 20, offset: 0 };
            const page1Options = { limit: 20, offset: 20 };

            const page0 = workflowStore.fetchWorkflowList("my", "", page0Options);
            const page1 = workflowStore.fetchWorkflowList("my", "", page1Options);

            expect(loadWorkflows).toHaveBeenCalledTimes(2);
            page0Response.resolve({ data: [workflowSummary("w0", "Page zero")], totalMatches: 2 });
            page1Response.resolve({ data: [workflowSummary("w1", "Page one")], totalMatches: 2 });
            const [page0Result, page1Result] = await Promise.all([page0, page1]);

            expect(page0Result.map((workflow) => workflow.id)).toEqual(["w0"]);
            expect(page1Result.map((workflow) => workflow.id)).toEqual(["w1"]);
            expect(workflowStore.getWorkflowList("my").map((workflow) => workflow.id)).toEqual(["w0", "w1"]);
        });

        it("keeps both pages when they are fetched one after the other", async () => {
            mockLoadWorkflowsOnce([workflowSummary("w0", "Page zero")]);
            await workflowStore.fetchWorkflowList("my", "", { limit: 1, offset: 0 });

            mockLoadWorkflowsOnce([workflowSummary("w1", "Page one")]);
            await workflowStore.fetchWorkflowList("my", "", { limit: 1, offset: 1 });

            expect(workflowStore.getWorkflowList("my").map((workflow) => workflow.id)).toEqual(["w0", "w1"]);
        });

        it("refreshes the head of the listing without dropping later pages", async () => {
            mockLoadWorkflowsOnce([workflowSummary("w0", "Page zero")]);
            await workflowStore.fetchWorkflowList("my", "", { limit: 1, offset: 0 });
            mockLoadWorkflowsOnce([workflowSummary("w1", "Page one")]);
            await workflowStore.fetchWorkflowList("my", "", { limit: 1, offset: 1 });

            mockLoadWorkflowsOnce([workflowSummary("w2", "Brand new")]);
            await workflowStore.fetchWorkflowList("my", "", { limit: 1, offset: 0 });

            expect(workflowStore.getWorkflowList("my").map((workflow) => workflow.id)).toEqual(["w2", "w0", "w1"]);
        });

        it("reads back a listing fetched with non-default options", async () => {
            mockLoadWorkflowsOnce([workflowSummary("w1", "First")]);

            await workflowStore.fetchWorkflowList("my", "", { limit: 25 });

            // consumers hydrate with their own page size but read the listing
            // without repeating it
            expect(workflowStore.isWorkflowListLoaded("my")).toBe(true);
            expect(workflowStore.getWorkflowList("my").map((workflow) => workflow.id)).toEqual(["w1"]);
        });

        it("refetches after a previous fetch settled", async () => {
            mockLoadWorkflowsOnce([]);
            await workflowStore.fetchWorkflowList("my");

            mockLoadWorkflowsOnce([workflowSummary("w1", "First")]);
            await workflowStore.fetchWorkflowList("my");

            expect(loadWorkflows).toHaveBeenCalledTimes(2);
            expect(workflowStore.getWorkflowList("my")).toHaveLength(1);
        });

        it("reports whether a list has been loaded and does not cache failed fetches", async () => {
            expect(workflowStore.isWorkflowListLoaded("my")).toBe(false);

            vi.mocked(loadWorkflows).mockRejectedValueOnce(new Error("boom"));
            await expect(workflowStore.fetchWorkflowList("my")).rejects.toThrow("boom");
            expect(workflowStore.isWorkflowListLoaded("my")).toBe(false);

            mockLoadWorkflowsOnce([]);
            await workflowStore.fetchWorkflowList("my");
            expect(workflowStore.isWorkflowListLoaded("my")).toBe(true);
        });
    });
});
