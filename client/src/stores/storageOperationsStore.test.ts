import { getFakeStorageOperationRun } from "@tests/test-data/storageOperations";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { isTerminalRunState, type TrackedStorageRun } from "@/utils/storageOperations";

import { useStorageOperationsStore } from "./storageOperationsStore";
import { setupTestPinia } from "./testUtils";

function createTrackedRun(
    runId: string,
    historyId: string,
    overrides: Partial<TrackedStorageRun> = {},
): TrackedStorageRun {
    return {
        ...getFakeStorageOperationRun({ run_id: runId }),
        historyId,
        runUrl: `/histories/${historyId}/storage/runs/${runId}`,
        ...overrides,
    };
}

describe("storageOperationsStore", () => {
    beforeEach(() => {
        setupTestPinia();
        localStorage.clear();
        vi.useFakeTimers();
        vi.setSystemTime(new Date("2026-01-01T00:00:00.000Z"));
    });

    afterEach(() => {
        vi.useRealTimers();
        localStorage.clear();
    });

    it("removes a tracked active run when it is cleared", () => {
        const store = useStorageOperationsStore();
        store.startRun(createTrackedRun("run_1", "history_1", { total_count: 2 }));

        expect(store.getRuns("history_1")).toHaveLength(1);
        expect(store.getActiveRuns("history_1")).toHaveLength(1);
        expect(store.getCompletedRuns("history_1")).toHaveLength(0);
        expect(store.getActiveRunCount("history_1")).toBe(1);

        store.clearRun("run_1");
        expect(store.getRuns("history_1")).toHaveLength(0);
    });

    it("excludes a run started 26 hours ago while retaining a fresh run", () => {
        const store = useStorageOperationsStore();
        store.startRun(createTrackedRun("fresh_run", "history_1"));
        store.startRun(
            createTrackedRun("expired_run", "history_1", {
                create_time: "2025-12-30T22:00:00.000Z",
                update_time: "2025-12-30T22:00:00.000Z",
            }),
        );

        expect(store.getRuns("history_1")).toHaveLength(1);
        expect(store.getRuns("history_1")[0]?.run_id).toBe("fresh_run");
        expect(store.getActiveRuns("history_1")).toHaveLength(1);
    });

    it("moves a run from active to completed and retains its final counts", () => {
        const store = useStorageOperationsStore();
        store.startRun(createTrackedRun("run_1", "history_1", { total_count: 10 }));

        expect(store.getActiveRunCount("history_1")).toBe(1);
        expect(store.getCompletedRunCount("history_1")).toBe(0);

        store.updateRunStatus("run_1", {
            state: "completed",
            succeeded_count: 10,
            failed_count: 0,
            skipped_count: 0,
            total_bytes_processed: 123,
            update_time: "2026-01-01T00:00:01.000Z",
        });

        expect(store.getActiveRunCount("history_1")).toBe(0);
        expect(store.getCompletedRunCount("history_1")).toBe(1);

        const completedRun = store.getCompletedRuns("history_1")[0];
        expect(completedRun).toBeDefined();
        expect(isTerminalRunState(completedRun!.state)).toBe(true);
        expect(completedRun!.state).toBe("completed");
        expect(completedRun!.succeeded_count).toBe(10);
        expect(completedRun!.total_bytes_processed).toBe(123);
    });

    it("lists a new run under its history", () => {
        const store = useStorageOperationsStore();
        store.startRun(createTrackedRun("run_2", "history_2", { total_count: 3 }));

        expect(store.getRuns("history_2")).toHaveLength(1);
        expect(store.getRuns("history_2")[0]?.run_id).toBe("run_2");
    });
});
