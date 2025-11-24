import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";

import { getWorkflowFull } from "@/components/Workflow/workflows.services";
import { useWorkflowStore } from "@/stores/workflowStore";

// Mock `getWorkflowFull` function
jest.mock("@/components/Workflow/workflows.services", () => ({
    getWorkflowFull: jest.fn(),
}));

const mockWorkflow = {
    id: "workflow-123",
    name: "Test Workflow",
    version: 1,
    steps: {},
};

describe("useWorkflowStore", () => {
    let workflowStore: ReturnType<typeof useWorkflowStore>;

    beforeEach(() => {
        setActivePinia(createPinia());
        workflowStore = useWorkflowStore();
        jest.clearAllMocks();
    });

    describe("getFullWorkflowCached", () => {
        it("should fetch workflow when not cached", async () => {
            (getWorkflowFull as jest.Mock).mockResolvedValue(mockWorkflow);

            const result = await workflowStore.getFullWorkflowCached("workflow-123", 1);
            await flushPromises();

            expect(getWorkflowFull).toHaveBeenCalledTimes(1);
            expect(getWorkflowFull).toHaveBeenCalledWith("workflow-123", 1);
            expect(result).toEqual(mockWorkflow);
        });

        it("should return cached workflow on subsequent calls", async () => {
            (getWorkflowFull as jest.Mock).mockResolvedValue(mockWorkflow);

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
            (getWorkflowFull as jest.Mock).mockReturnValue(workflowPromise);

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

            (getWorkflowFull as jest.Mock).mockResolvedValueOnce(mockWorkflow1);
            (getWorkflowFull as jest.Mock).mockResolvedValueOnce(mockWorkflow2);

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

            (getWorkflowFull as jest.Mock).mockResolvedValueOnce(mockWorkflowV1);
            (getWorkflowFull as jest.Mock).mockResolvedValueOnce(mockWorkflowV2);

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
            (getWorkflowFull as jest.Mock).mockReturnValue(workflowPromise);

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
});
