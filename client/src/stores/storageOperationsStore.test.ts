import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { isTerminalRunState } from "@/utils/storageOperations";

import { useStorageOperationsStore } from "./storageOperationsStore";

function createTestRun(runId: string, historyId: string, startedAt?: Date | string) {
    const timestamp = startedAt instanceof Date ? startedAt.toISOString() : startedAt || new Date().toISOString();
    return {
        historyId,
        runUrl: `/histories/${historyId}/storage/runs/${runId}`,
        run_id: runId,
        state: "pending" as const,
        mode: "move" as const,
        target_object_store_id: "other",
        create_time: timestamp,
        update_time: timestamp,
        total_count: 1,
        succeeded_count: 0,
        failed_count: 0,
        skipped_count: 0,
        total_bytes_processed: 0,
    };
}

describe("storageOperationsStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        localStorage.clear();
    });

    it("tracks and clears runs", () => {
        const store = useStorageOperationsStore();

        store.startRun({
            ...createTestRun("run_1", "history_1"),
            total_count: 2,
        });

        expect(store.getRuns("history_1")).toHaveLength(1);
        expect(store.getActiveRuns("history_1")).toHaveLength(1);
        expect(store.getCompletedRuns("history_1")).toHaveLength(0);
        expect(store.getActiveRunCount("history_1")).toBe(1);

        store.clearRun("run_1");
        expect(store.getRuns("history_1")).toHaveLength(0);
    });

    it("drops expired runs when listing", () => {
        vi.useFakeTimers();
        const store = useStorageOperationsStore();
        const now = new Date("2026-01-01T00:00:00Z");
        vi.setSystemTime(now);

        store.startRun(createTestRun("fresh_run", "history_1", now));

        store.startRun(createTestRun("expired_run", "history_1", new Date(now.getTime() - 26 * 60 * 60 * 1000)));

        expect(store.getRuns("history_1")).toHaveLength(1);
        expect(store.getRuns("history_1")[0]?.run_id).toBe("fresh_run");
        expect(store.getActiveRuns("history_1")).toHaveLength(1);

        vi.useRealTimers();
    });

    it("distinguishes active and completed runs", () => {
        vi.useFakeTimers();
        const store = useStorageOperationsStore();
        const now = new Date("2026-01-01T00:00:00Z");
        vi.setSystemTime(now);

        // Start a run
        store.startRun({
            ...createTestRun("run_1", "history_1", now),
            total_count: 10,
        });

        expect(store.getActiveRunCount("history_1")).toBe(1);
        expect(store.getCompletedRunCount("history_1")).toBe(0);

        // Mark as completed
        store.updateRunStatus("run_1", {
            state: "completed",
            succeeded_count: 10,
            failed_count: 0,
            skipped_count: 0,
            total_bytes_processed: 123,
            update_time: new Date(now.getTime() + 1000).toISOString(),
        });

        expect(store.getActiveRunCount("history_1")).toBe(0);
        expect(store.getCompletedRunCount("history_1")).toBe(1);

        const completedRun = store.getCompletedRuns("history_1")[0];
        if (completedRun) {
            expect(isTerminalRunState(completedRun.state)).toBe(true);
            expect(completedRun.state).toBe("completed");
            expect(completedRun.succeeded_count).toBe(10);
            expect(completedRun.total_bytes_processed).toBe(123);
        }

        vi.useRealTimers();
    });

    it("startRun creates a new run", () => {
        const store = useStorageOperationsStore();

        store.startRun({
            ...createTestRun("run_2", "history_2"),
            total_count: 3,
        });

        expect(store.getRuns("history_2")).toHaveLength(1);
        expect(store.getRuns("history_2")[0]?.run_id).toBe("run_2");
    });
});
