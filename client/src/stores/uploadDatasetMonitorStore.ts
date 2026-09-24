import { defineStore } from "pinia";
import { computed, onScopeDispose, watch } from "vue";

import { type HDASummary, isHDA, isHDCA } from "@/api";
import { ERROR_DATASET_STATES, TERMINAL_DATASET_STATES } from "@/api/datasets";
import {
    getContentItemState,
    isErrorCollectionState,
    isTerminalCollectionState,
    type State,
    stateText,
} from "@/components/History/Content/model/states";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import { useTerminalStateMonitor } from "@/composables/useTerminalStateMonitor";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";

type PendingEntry =
    | { kind: "datasets"; uploadId: string; historyId: string; datasetIds: string[] }
    | { kind: "collection"; uploadId: string; historyId: string; collectionId: string };

const MONITOR_FILTER = "deleted:any visible:any";
const PROCESSING_TIMEOUT_MS = 30 * 60 * 1000;
const GIVE_UP_CHECK_INTERVAL_MS = 60 * 1000;

export const useUploadDatasetMonitorStore = defineStore("uploadDatasetMonitor", () => {
    const uploadState = useUploadState();
    const historyItemsStore = useHistoryItemsStore();
    const missingSince = new Map<string, number>();

    const pendingEntries = computed<PendingEntry[]>(() => {
        const entries: PendingEntry[] = [];

        for (const item of uploadState.activeItems.value) {
            if (item.status === "processing" && item.datasetIds.length > 0) {
                entries.push({
                    kind: "datasets",
                    uploadId: item.id,
                    historyId: item.targetHistoryId,
                    datasetIds: item.datasetIds,
                });
            }
        }

        for (const batch of uploadState.activeBatches.value) {
            if (batch.status === "processing" && batch.collectionId) {
                entries.push({
                    kind: "collection",
                    uploadId: batch.id,
                    historyId: batch.historyId,
                    collectionId: batch.collectionId,
                });
            }
        }

        return entries;
    });

    const isMonitoring = computed(() => pendingEntries.value.length > 0);

    const pendingHistoryIds = computed<string[]>(() => [
        ...new Set(pendingEntries.value.map((entry) => entry.historyId)),
    ]);

    const { syncPollers } = useTerminalStateMonitor(pendingHistoryIds, (historyId) =>
        historyItemsStore.fetchHistoryItems(historyId, MONITOR_FILTER, 0),
    );

    function findHistoryItem(historyId: string, id: string) {
        return historyItemsStore.getHistoryItems(historyId, MONITOR_FILTER).find((item) => item.id === id);
    }

    function forgetMissing(uploadId: string) {
        missingSince.delete(uploadId);
    }

    function checkMissingTimeout(uploadId: string, onTimeout: () => void) {
        const now = Date.now();
        const firstSeen = missingSince.get(uploadId);
        if (firstSeen === undefined) {
            missingSince.set(uploadId, now);
            return;
        }
        if (now - firstSeen >= PROCESSING_TIMEOUT_MS) {
            missingSince.delete(uploadId);
            onTimeout();
        }
    }

    function resolveEntry(entry: PendingEntry) {
        if (entry.kind === "collection") {
            resolveCollectionEntry(entry);
            return;
        }

        const item = uploadState.activeItems.value.find((u) => u.id === entry.uploadId);
        if (!item || item.status !== "processing") {
            forgetMissing(entry.uploadId);
            return;
        }

        const datasets: HDASummary[] = [];
        for (const dsId of entry.datasetIds) {
            const found = findHistoryItem(entry.historyId, dsId);
            if (found && isHDA(found)) {
                datasets.push(found);
            }
        }

        if (datasets.length < entry.datasetIds.length) {
            checkMissingTimeout(entry.uploadId, () =>
                uploadState.markDatasetsFailed(
                    entry.uploadId,
                    "Dataset is no longer available in the history and will not finish processing.",
                ),
            );
            return;
        }
        forgetMissing(entry.uploadId);

        const states = datasets.map((ds) => ds.state ?? "new");
        const errorState = states.find((s) => ERROR_DATASET_STATES.includes(s));
        const allTerminal = states.every((s) => TERMINAL_DATASET_STATES.includes(s));

        if (errorState) {
            uploadState.markDatasetsFailed(entry.uploadId, stateText(errorState));
        } else if (allTerminal) {
            uploadState.markDatasetsResolved(entry.uploadId);
        } else {
            const activeState = states.find((s) => !TERMINAL_DATASET_STATES.includes(s));
            if (activeState) {
                uploadState.updateDatasetState(entry.uploadId, activeState as State);
            }
        }
    }

    function resolveCollectionEntry(entry: Extract<PendingEntry, { kind: "collection" }>) {
        const batch = uploadState.getBatch(entry.uploadId);
        if (!batch || batch.status !== "processing") {
            forgetMissing(entry.uploadId);
            return;
        }

        const hdca = findHistoryItem(entry.historyId, entry.collectionId);
        if (!hdca || !isHDCA(hdca)) {
            checkMissingTimeout(entry.uploadId, () =>
                uploadState.markBatchFailed(
                    entry.uploadId,
                    "Collection is no longer available in the history and will not finish processing.",
                ),
            );
            return;
        }
        forgetMissing(entry.uploadId);

        const state = getContentItemState(hdca);
        if (isErrorCollectionState(state)) {
            uploadState.markBatchFailed(entry.uploadId, stateText(state));
        } else if (isTerminalCollectionState(state)) {
            uploadState.markBatchResolved(entry.uploadId);
        }
    }

    function resolveEntries() {
        for (const entry of [...pendingEntries.value]) {
            resolveEntry(entry);
        }
    }

    function pruneMissing() {
        const pendingIds = new Set(pendingEntries.value.map((e) => e.uploadId));
        for (const uploadId of [...missingSince.keys()]) {
            if (!pendingIds.has(uploadId)) {
                missingSince.delete(uploadId);
            }
        }
    }

    function resolveAndSync() {
        resolveEntries();
        pruneMissing();
        syncPollers();
    }

    const watchedStates = computed(() =>
        pendingEntries.value
            .map((entry) => {
                if (entry.kind === "collection") {
                    const hdca = findHistoryItem(entry.historyId, entry.collectionId);
                    return hdca && isHDCA(hdca) ? getContentItemState(hdca) : "?";
                }
                return entry.datasetIds
                    .map((id) => {
                        const found = findHistoryItem(entry.historyId, id);
                        return found && isHDA(found) ? (found.state ?? "new") : "?";
                    })
                    .join(",");
            })
            .join("|"),
    );

    watch(pendingEntries, resolveAndSync, { immediate: true });

    watch(watchedStates, resolveAndSync);

    const giveUpTimer = setInterval(() => {
        if (isMonitoring.value) {
            resolveAndSync();
        }
    }, GIVE_UP_CHECK_INTERVAL_MS);
    (giveUpTimer as unknown as { unref?: () => void }).unref?.();

    onScopeDispose(() => {
        clearInterval(giveUpTimer);
        missingSince.clear();
    });

    return { isMonitoring };
});
