import { defineStore } from "pinia";
import { computed, type ComputedRef, shallowReactive, watch } from "vue";

import { GalaxyApi } from "@/api";
import { useDownloadTracker } from "@/composables/downloadTracker";
import type { TaskMonitor } from "@/composables/genericTaskMonitor";
import type { MonitoringData } from "@/composables/persistentProgressMonitor";
import { READY_STATE } from "@/composables/shortTermStorageMonitor";
import { useTaskMonitor } from "@/composables/taskMonitor";
import type { ExportableItem } from "@/stores/exportToAnotherGalaxyStore";
import { absPath, withPrefix } from "@/utils/redirect";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

const POLL_DELAY = 3000;
// A short network problem should not fail an export that keeps running on the server.
const MAX_STATUS_FAILURES = 3;
// Well inside the shortest storage duration a server is likely to use, so a reused link still works.
const REUSE_FOR_MS = 60 * 60 * 1000;

export type ExportForAnotherGalaxyStatus = "starting" | "running" | "ready" | "failed";

export interface ExportForAnotherGalaxyState {
    status: ExportForAnotherGalaxyStatus;
    /** Download link for the other Galaxy, once the export is ready. */
    link?: string;
    /** Why the export failed. */
    error?: string;
}

interface Export {
    storageRequestId: string;
    taskId: string;
    startedAt: number;
    monitor: TaskMonitor;
}

// Dataset and collection ids can be equal, so the type is part of the key.
function keyOf(item: ExportableItem) {
    return `${item.contentType}:${item.contentId}`;
}

async function prepareExport(item: ExportableItem) {
    const { data, error } = await GalaxyApi().POST(
        "/api/histories/{history_id}/contents/{type}s/{id}/prepare_store_download",
        {
            params: {
                path: { history_id: item.historyId, type: item.contentType, id: item.contentId },
            },
            body: { model_store_format: "tar.gz", include_files: true, include_deleted: false, include_hidden: false },
        },
    );
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

// One set of exports per page; only functions are returned, as store state would unwrap the monitors' refs.
const useExports = defineStore("exportsForAnotherGalaxy", () => {
    const exports = shallowReactive(new Map<string, Export>());
    // Items whose export request has not come back yet, so a second start does not export them again.
    const starting = shallowReactive(new Set<string>());
    const startErrors = shallowReactive(new Map<string, string>());

    const { trackDownloadRequestWithData } = useDownloadTracker();

    // Recent Exports only learns from the storage, which a failed export also marks ready, so tell it the outcome.
    function recordOutcome(monitor: TaskMonitor, tracked: MonitoringData) {
        const stop = watch(
            [monitor.isCompleted, monitor.hasFailed, monitor.failureReason],
            ([completed, failed, failureReason]) => {
                if (completed) {
                    trackDownloadRequestWithData({ ...tracked, taskStatus: READY_STATE, isFinal: true });
                    stop();
                } else if (failed) {
                    // Any state but ready or pending reads as failed there. The reason comes in a second request.
                    trackDownloadRequestWithData({ ...tracked, taskStatus: "FAILURE", failureReason, isFinal: true });
                    if (failureReason !== undefined) {
                        stop();
                    }
                }
            },
        );
    }

    async function startExport(item: ExportableItem) {
        const key = keyOf(item);
        if (starting.has(key)) {
            return;
        }
        const existing = exports.get(key);
        if (existing && !existing.monitor.hasFailed.value && Date.now() - existing.startedAt < REUSE_FOR_MS) {
            if (existing.monitor.requestHasFailed.value) {
                existing.monitor.waitForTask(existing.taskId, POLL_DELAY);
            }
            return;
        }
        existing?.monitor.stopWaitingForTask();
        exports.delete(key);
        startErrors.delete(key);
        let data;
        starting.add(key);
        try {
            data = await prepareExport(item);
        } catch (e) {
            startErrors.set(key, errorMessageAsString(e));
            return;
        } finally {
            starting.delete(key);
        }
        const tracked: MonitoringData = {
            taskId: data.storage_request_id,
            taskType: "short_term_storage",
            request: {
                source: "history-content-export",
                taskType: "short_term_storage",
                action: "export",
                object: {
                    id: item.contentId,
                    type: item.contentType === "dataset_collection" ? "collection" : "dataset",
                    name: item.contentName,
                },
                description: `Export of ${item.contentName} for another Galaxy`,
            },
            startedAt: new Date(),
            isFinal: false,
        };
        trackDownloadRequestWithData(tracked);
        const monitor = useTaskMonitor({ maxRequestFailures: MAX_STATUS_FAILURES });
        recordOutcome(monitor, tracked);
        exports.set(key, {
            storageRequestId: data.storage_request_id,
            taskId: data.task.id,
            startedAt: Date.now(),
            monitor,
        });
        monitor.waitForTask(data.task.id, POLL_DELAY);
    }

    function stateOf(item: ExportableItem): ExportForAnotherGalaxyState | undefined {
        const key = keyOf(item);
        if (starting.has(key)) {
            return { status: "starting" };
        }
        const startError = startErrors.get(key);
        if (startError !== undefined) {
            return { status: "failed", error: startError };
        }
        const entry = exports.get(key);
        if (!entry) {
            return undefined;
        }
        const { monitor } = entry;
        if (monitor.hasFailed.value) {
            return { status: "failed", error: monitor.failureReason.value || "The export failed." };
        }
        if (monitor.requestHasFailed.value) {
            return { status: "failed", error: "Galaxy could not say how the export is going. Please try again later." };
        }
        // The export task's own state, not the storage's: a failed export still marks its storage ready.
        if (monitor.isCompleted.value) {
            return { status: "ready", link: absPath(withPrefix(`/api/short_term_storage/${entry.storageRequestId}`)) };
        }
        return { status: "running" };
    }

    function stopAll() {
        exports.forEach((entry) => entry.monitor.stopWaitingForTask());
    }

    return { startExport, stateOf, stopAll };
});

/**
 * Exports history items for another Galaxy to import, as a short term storage link each. Exports are shared by
 * every caller and keep running when the component that started them goes away.
 */
export function useExportForAnotherGalaxy() {
    const store = useExports();

    /**
     * Starts exporting the item, or reuses its export if one is running, finished within the last hour, or
     * could not be checked (which is then checked again).
     * @returns The export's state, kept up to date.
     */
    function start(item: ExportableItem): ComputedRef<ExportForAnotherGalaxyState> {
        store.startExport(item);
        return computed(() => store.stateOf(item) ?? { status: "starting" });
    }

    return {
        start,
        /** The state of the item's export, or undefined if it was never started. */
        stateOf: store.stateOf,
        /** Stops following every export, for when the page goes away. */
        stopAll: store.stopAll,
    };
}
