import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { WorkflowSummary } from "@/api/workflows";
import { loadWorkflows } from "@/api/workflows";
import { getWorkflowFull } from "@/components/Workflow/workflows.services";
import { useWorkflowStore } from "@/stores/workflowStore";

// Mock `getWorkflowFull` function
vi.mock("@/components/Workflow/workflows.services", () => ({
    getWorkflowFull: vi.fn(),
}));

// Mock the workflows API layer used by the list cache
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
    return { id, name, update_time: "2026-08-31T10:00:00", ...extra } as WorkflowSummary;
}

function mockLoadWorkflowsOnce(data: WorkflowSummary[]) {
    vi.mocked(loadWorkflows).mockResolvedValueOnce({ data, totalMatches: data.length });
}

describe("useWorkflowStore", () => {
    let workflowStore: ReturnType<typeof useWorkflowStore>;

    beforeEach(() => {
        setActivePinia(createPinia());
        workflowStore = useWorkflowStore();
        vi.clearAllMocks();
    });

    describe("getFullWorkflowCached", () => {
        it("should fetch workflow when not cached", async () => {
            vi.mocked(getWorkflowFull).mockResolvedValue(mockWorkflow);

            const result = await workflowStore.getFullWorkflowCached("workflow-123", 1);
            await flushPromises();

            expect(getWorkflowFull).toHaveBeenCalledTimes(1);
            expect(getWorkflowFull).toHaveBeenCalledWith("workflow-123", 1);
            expect(result).toEqual(mockWorkflow);
        });

        it("should return cached workflow on subsequent calls", async () => {
            vi.mocked(getWorkflowFull).mockResolvedValue(mockWorkflow);

            // First call - should fetch
            const result1 = await workflowStore.getFullWorkflowCached("workflow-123", 1);
            await flushPromises();
            expect(getWorkflowFull).toHaveBeenCalledTimes(1);
            expect(result1).toEqual(mockWorkflow);

            // Second call - should return cached
            const result2 = await workflowStore.getFullWorkflowCached("workflow-123", 1);
            await flushPromises();

            // Still only one API call
            expect(getWorkflowFull).toHaveBeenCalledTimes(1);
            expect(result2).toEqual(mockWorkflow);
        });

        it("should prevent duplicate concurrent requests for same workflow", async () => {
            // Create a promise that we can control when it resolves
            let resolveWorkflow: (value: any) => void;
            const workflowPromise = new Promise((resolve) => {
                resolveWorkflow = resolve;
            });
            vi.mocked(getWorkflowFull).mockReturnValue(workflowPromise);

            // Start two concurrent requests for the same workflow
            const promise1 = workflowStore.getFullWorkflowCached("workflow-123", 1);
            const promise2 = workflowStore.getFullWorkflowCached("workflow-123", 1);

            // At this point, getWorkflowFull should only be called once
            expect(getWorkflowFull).toHaveBeenCalledTimes(1);

            // Resolve the workflow promise
            resolveWorkflow!(mockWorkflow);
            await flushPromises();

            // Both promises should resolve with the same workflow
            const [result1, result2] = await Promise.all([promise1, promise2]);
            expect(result1).toEqual(mockWorkflow);
            expect(result2).toEqual(mockWorkflow);

            // Still only one API call
            expect(getWorkflowFull).toHaveBeenCalledTimes(1);
        });

        it("should allow concurrent requests for different workflows", async () => {
            const mockWorkflow1 = { ...mockWorkflow, id: "workflow-1" };
            const mockWorkflow2 = { ...mockWorkflow, id: "workflow-2" };

            vi.mocked(getWorkflowFull).mockResolvedValueOnce(mockWorkflow1);
            vi.mocked(getWorkflowFull).mockResolvedValueOnce(mockWorkflow2);

            // Start concurrent requests for different workflows
            const [result1, result2] = await Promise.all([
                workflowStore.getFullWorkflowCached("workflow-1"),
                workflowStore.getFullWorkflowCached("workflow-2"),
            ]);
            await flushPromises();

            // Should make two separate API calls
            expect(getWorkflowFull).toHaveBeenCalledTimes(2);
            expect(result1).toEqual(mockWorkflow1);
            expect(result2).toEqual(mockWorkflow2);
        });

        it("should allow concurrent requests for different versions of same workflow", async () => {
            const mockWorkflowV1 = { ...mockWorkflow, version: 1 };
            const mockWorkflowV2 = { ...mockWorkflow, version: 2 };

            vi.mocked(getWorkflowFull).mockResolvedValueOnce(mockWorkflowV1);
            vi.mocked(getWorkflowFull).mockResolvedValueOnce(mockWorkflowV2);

            // Start concurrent requests for different versions
            const [result1, result2] = await Promise.all([
                workflowStore.getFullWorkflowCached("workflow-123", 1),
                workflowStore.getFullWorkflowCached("workflow-123", 2),
            ]);
            await flushPromises();

            // Should make two separate API calls
            expect(getWorkflowFull).toHaveBeenCalledTimes(2);
            expect(result1).toEqual(mockWorkflowV1);
            expect(result2).toEqual(mockWorkflowV2);
        });

        it("should deduplicate multiple concurrent requests", async () => {
            // Mock API response which we can resolve later
            let resolveWorkflow: (value: any) => void;
            const workflowPromise = new Promise((resolve) => {
                resolveWorkflow = resolve;
            });
            vi.mocked(getWorkflowFull).mockReturnValue(workflowPromise);

            // Start 5 concurrent requests
            const promises = [
                workflowStore.getFullWorkflowCached("workflow-123", 1),
                workflowStore.getFullWorkflowCached("workflow-123", 1),
                workflowStore.getFullWorkflowCached("workflow-123", 1),
                workflowStore.getFullWorkflowCached("workflow-123", 1),
                workflowStore.getFullWorkflowCached("workflow-123", 1),
            ];

            // Only one API call should be made
            expect(getWorkflowFull).toHaveBeenCalledTimes(1);

            // Resolving the API call
            resolveWorkflow!(mockWorkflow);
            await flushPromises();

            // All 5 promises should resolve with the same result
            const results = await Promise.all(promises);
            results.forEach((result) => {
                expect(result).toEqual(mockWorkflow);
            });

            // Still only one API call total
            expect(getWorkflowFull).toHaveBeenCalledTimes(1);
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

            mockLoadWorkflowsOnce([workflowSummary("w1", "New name")]);
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
            type WorkflowListResult = { data: WorkflowSummary[]; totalMatches: number };
            let resolvePage0: (result: WorkflowListResult) => void = () => undefined;
            let resolvePage1: (result: WorkflowListResult) => void = () => undefined;
            vi.mocked(loadWorkflows).mockImplementation(({ offset }) => {
                return new Promise((resolve) => {
                    if (offset === 0) {
                        resolvePage0 = resolve;
                    } else {
                        resolvePage1 = resolve;
                    }
                });
            });
            const page0Options = { limit: 20, offset: 0 };
            const page1Options = { limit: 20, offset: 20 };

            const page0 = workflowStore.fetchWorkflowList("my", "", page0Options);
            const page1 = workflowStore.fetchWorkflowList("my", "", page1Options);

            expect(loadWorkflows).toHaveBeenCalledTimes(2);
            resolvePage0({ data: [workflowSummary("w0", "Page zero")], totalMatches: 2 });
            resolvePage1({ data: [workflowSummary("w1", "Page one")], totalMatches: 2 });
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
