import { computed, readonly, type Ref, ref } from "vue";

import { getStorageOperationRunStatus, type HistoryReference, type StorageOperationRunResponse } from "@/api/histories";
import { useResourceWatcher } from "@/composables/resourceWatcher";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";
import { useStorageOperationsStore } from "@/stores/storageOperationsStore";
import { useUserStore } from "@/stores/userStore";
import { isTerminalRunState } from "@/utils/storageOperations";

const STORAGE_RUN_POLLING_INTERVAL = 10000; // 10 seconds

export interface StorageRunWatcherOptions {
    pollInterval?: number;
    enableBackgroundPolling?: boolean;
}

const DEFAULT_RUN_WATCHER_OPTIONS: Required<StorageRunWatcherOptions> = {
    pollInterval: STORAGE_RUN_POLLING_INTERVAL,
    enableBackgroundPolling: false,
};

type RunSummaries = Record<string, StorageOperationRunResponse["run"]>;

interface SharedHistoryWatcher {
    runSummariesByRunId: Ref<RunSummaries>;
    isPolling: Readonly<Ref<boolean>>;
    startPolling: () => void;
    stopPolling: () => void;
    activePollers: number;
}

const sharedHistoryWatchers = new Map<string, SharedHistoryWatcher>();

function resolveWatcherOptions(options?: StorageRunWatcherOptions): Required<StorageRunWatcherOptions> {
    return {
        ...DEFAULT_RUN_WATCHER_OPTIONS,
        ...options,
    };
}

/**
 * Poll storage-operation run status until it reaches a terminal state.
 */
export function useStorageRunWatcher(history: HistoryReference, runId: string, options?: StorageRunWatcherOptions) {
    const { pollInterval, enableBackgroundPolling } = resolveWatcherOptions(options);
    const runStatus = ref<StorageOperationRunResponse | null>(null);
    const isTerminal = computed(() => {
        const state = runStatus.value?.run.state;
        return state !== undefined && isTerminalRunState(state);
    });

    async function fetchStatus() {
        const data = await getStorageOperationRunStatus(history, runId);
        runStatus.value = data ?? null;
        if (isTerminal.value) {
            stopPolling();
        }
    }

    const { startWatchingResource: startPolling, stopWatchingResource: stopPolling } = useResourceWatcher(fetchStatus, {
        shortPollingInterval: pollInterval,
        enableBackgroundPolling,
    });

    return { runStatus, isTerminal, startPolling, stopPolling };
}

/**
 * Poll status for all tracked storage-operation runs in a history.
 * The watcher is shared across all components that call this function with the same historyId, so they will all see the same run statuses and share the polling.
 * Polling will only be active when at least one component is using the watcher, and will stop when no components are using it.
 */
export function useStorageHistoryRunsWatcher(historyId: string, options?: StorageRunWatcherOptions) {
    const { pollInterval, enableBackgroundPolling } = resolveWatcherOptions(options);

    let watcher = sharedHistoryWatchers.get(historyId);

    if (!watcher) {
        const storageOperationsStore = useStorageOperationsStore();
        const userStore = useUserStore();
        const quotaUsageStore = useQuotaUsageStore();
        const runSummariesByRunId = ref<RunSummaries>({});

        const historyReference: HistoryReference = {
            id: historyId,
            model_class: "History",
        };

        const watchStorageOperationRuns = async () => {
            const runs = storageOperationsStore.getRuns(historyId);
            if (!runs.length) {
                runSummariesByRunId.value = {};
                return;
            }

            const previous = runSummariesByRunId.value;

            const runsToFetch = runs.filter((run) => !isTerminalRunState(run.state));

            if (!runsToFetch.length) {
                const nextFromPrevious: RunSummaries = {};
                runs.forEach((run) => {
                    const summary = previous[run.run_id];
                    if (summary) {
                        nextFromPrevious[run.run_id] = summary;
                    }
                });
                runSummariesByRunId.value = nextFromPrevious;
                return;
            }

            const settled = await Promise.allSettled(
                runsToFetch.map(async (run) => {
                    const status = await getStorageOperationRunStatus(historyReference, run.run_id);
                    return { run_id: run.run_id, summary: status?.run };
                }),
            );

            const next: RunSummaries = {};
            let hasNewlyTerminalRun = false;

            runs.forEach((run) => {
                const existingSummary = previous[run.run_id];
                if (existingSummary) {
                    next[run.run_id] = existingSummary;
                }
            });

            settled.forEach((result, index) => {
                const runId = runsToFetch[index]?.run_id;
                if (!runId) {
                    return;
                }

                if (result.status === "fulfilled" && result.value.summary) {
                    const summary = result.value.summary;
                    const previouslyTerminal = isTerminalRunState(runsToFetch[index]?.state ?? summary.state);
                    next[runId] = summary;
                    storageOperationsStore.updateRunStatus(runId, {
                        state: summary.state,
                        total_count: summary.total_count,
                        succeeded_count: summary.succeeded_count,
                        failed_count: summary.failed_count,
                        skipped_count: summary.skipped_count,
                        total_bytes_processed: summary.total_bytes_processed,
                        update_time: summary.update_time,
                    });
                    if (!previouslyTerminal && isTerminalRunState(summary.state)) {
                        hasNewlyTerminalRun = true;
                    }
                }
            });

            runSummariesByRunId.value = next;

            if (hasNewlyTerminalRun) {
                void userStore.refreshUser(false);
                quotaUsageStore.requestRefreshDebounced(0);
            }
        };

        const { startWatchingResource, stopWatchingResource, isWatchingResource } = useResourceWatcher(
            watchStorageOperationRuns,
            {
                shortPollingInterval: pollInterval,
                enableBackgroundPolling,
            },
        );

        watcher = {
            runSummariesByRunId,
            isPolling: readonly(isWatchingResource),
            startPolling: startWatchingResource,
            stopPolling: stopWatchingResource,
            activePollers: 0,
        };

        sharedHistoryWatchers.set(historyId, watcher);
    }

    const sharedWatcher = watcher;
    let hasStartedPolling = false;

    function startPolling() {
        if (hasStartedPolling) {
            return;
        }
        hasStartedPolling = true;
        sharedWatcher.activePollers += 1;
        if (sharedWatcher.activePollers === 1) {
            sharedWatcher.startPolling();
        }
    }

    function stopPolling() {
        if (!hasStartedPolling) {
            return;
        }
        hasStartedPolling = false;
        sharedWatcher.activePollers = Math.max(0, sharedWatcher.activePollers - 1);
        if (sharedWatcher.activePollers === 0) {
            sharedWatcher.stopPolling();
        }
    }

    return {
        isPolling: sharedWatcher.isPolling,
        startPolling,
        stopPolling,
        runSummariesByRunId: readonly(sharedWatcher.runSummariesByRunId),
    };
}
