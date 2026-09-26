import { defineStore } from "pinia";

import { useUserLocalStorage } from "@/composables/userLocalStorage";
import { isTerminalRunState, type StorageOperationRunSummary, type TrackedStorageRun } from "@/utils/storageOperations";

const ACTIVE_RUN_TTL_MS = 24 * 60 * 60 * 1000;

export type StorageRun = TrackedStorageRun;

export type RunStatusUpdate = {
    state: StorageOperationRunSummary["state"];
    succeeded_count?: StorageOperationRunSummary["succeeded_count"];
    failed_count?: StorageOperationRunSummary["failed_count"];
    skipped_count?: StorageOperationRunSummary["skipped_count"];
    total_count?: StorageOperationRunSummary["total_count"];
    total_bytes_processed?: StorageOperationRunSummary["total_bytes_processed"];
    update_time?: StorageOperationRunSummary["update_time"];
};

export const useStorageOperationsStore = defineStore("storageOperationsStore", () => {
    const runs = useUserLocalStorage<StorageRun[]>("storage-operations-active-runs", []);

    function isExpired(run: StorageRun): boolean {
        const startedAtRaw = run.create_time || run.update_time;
        if (!startedAtRaw) {
            return false;
        }

        const startedAt = Date.parse(startedAtRaw);
        if (!Number.isFinite(startedAt)) {
            return false;
        }

        return Date.now() - startedAt > ACTIVE_RUN_TTL_MS;
    }

    function pruneExpiredRuns() {
        runs.value = runs.value.filter((run) => !isExpired(run));
    }

    function startRun(run: StorageRun): void {
        pruneExpiredRuns();
        // Remove any existing run with the same ID
        runs.value = runs.value.filter((r) => r.run_id !== run.run_id);
        runs.value.push(run);
    }

    function updateRunStatus(runId: string, update: RunStatusUpdate): void {
        pruneExpiredRuns();
        runs.value = runs.value.map((run) => {
            if (run.run_id !== runId) {
                return run;
            }

            return {
                ...run,
                ...update,
            };
        });
    }

    function clearRun(runId: string): void {
        runs.value = runs.value.filter((run) => run.run_id !== runId);
    }

    function getRuns(historyId: string): StorageRun[] {
        return runs.value.filter((run) => run.historyId === historyId && !isExpired(run));
    }

    function getActiveRuns(historyId: string): StorageRun[] {
        return runs.value.filter(
            (run) => run.historyId === historyId && !isTerminalRunState(run.state) && !isExpired(run),
        );
    }

    function getCompletedRuns(historyId: string): StorageRun[] {
        return runs.value.filter(
            (run) => run.historyId === historyId && isTerminalRunState(run.state) && !isExpired(run),
        );
    }

    function getActiveRunCount(historyId: string): number {
        return getActiveRuns(historyId).length;
    }

    function getCompletedRunCount(historyId: string): number {
        return getCompletedRuns(historyId).length;
    }

    pruneExpiredRuns();

    return {
        runs,
        startRun,
        updateRunStatus,
        getRuns,
        getActiveRuns,
        getCompletedRuns,
        getActiveRunCount,
        getCompletedRunCount,
        clearRun,
    };
});
