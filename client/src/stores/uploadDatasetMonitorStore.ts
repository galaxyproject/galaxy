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
import { useResourceWatcher } from "@/composables/resourceWatcher";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";
import { useHistoryStore } from "@/stores/historyStore";

type PendingEntry =
    | { kind: "datasets"; uploadId: string; historyId: string; datasetIds: string[] }
    | { kind: "collection"; uploadId: string; historyId: string; collectionId: string };

export const useUploadDatasetMonitorStore = defineStore("uploadDatasetMonitor", () => {
    const uploadState = useUploadState();
    const historyItemsStore = useHistoryItemsStore();
    const historyStore = useHistoryStore();
    const pollers = new Map<string, ReturnType<typeof useResourceWatcher>>();

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

    function findHistoryItem(historyId: string, id: string) {
        return historyItemsStore.getHistoryItems(historyId, "").find((item) => item.id === id);
    }

    function resolveEntry(entry: PendingEntry) {
        if (entry.kind === "collection") {
            resolveCollectionEntry(entry);
            return;
        }

        const item = uploadState.activeItems.value.find((u) => u.id === entry.uploadId);
        if (!item || item.status !== "processing") {
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
            return;
        }

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
            return;
        }

        const hdca = findHistoryItem(entry.historyId, entry.collectionId);
        if (!hdca || !isHDCA(hdca)) {
            return;
        }

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

    function stopPoller(historyId: string) {
        pollers.get(historyId)?.stopWatchingResource();
        pollers.delete(historyId);
    }

    function ensureFallbackPoller(historyId: string) {
        if (pollers.has(historyId)) {
            return;
        }
        const watcher = useResourceWatcher(async () => {
            await historyItemsStore.fetchHistoryItems(historyId, "", 0);
        });
        pollers.set(historyId, watcher);
        watcher.startWatchingResource();
    }

    function syncPollers() {
        const currentId = historyStore.currentHistoryId;

        for (const historyId of pendingHistoryIds.value) {
            if (currentId && currentId !== historyId) {
                ensureFallbackPoller(historyId);
            }
        }

        for (const historyId of [...pollers.keys()]) {
            const stillPending = pendingEntries.value.some((e) => e.historyId === historyId);
            if (!stillPending || (currentId && currentId === historyId)) {
                stopPoller(historyId);
            }
        }
    }

    function resolveAndSync() {
        resolveEntries();
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

    watch(() => historyStore.currentHistoryId, syncPollers);

    onScopeDispose(() => {
        for (const historyId of [...pollers.keys()]) {
            stopPoller(historyId);
        }
    });

    return { isMonitoring };
});
