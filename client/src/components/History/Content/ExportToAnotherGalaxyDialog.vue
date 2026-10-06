<script setup lang="ts">
import { faCopy } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormInput, BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onUnmounted, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import { useDownloadTracker } from "@/composables/downloadTracker";
import type { MonitoringData } from "@/composables/persistentProgressMonitor";
import { useShortTermStorage } from "@/composables/shortTermStorage";
import { READY_STATE } from "@/composables/shortTermStorageMonitor";
import { useTaskMonitor } from "@/composables/taskMonitor";
import { type ExportableItem, useExportToAnotherGalaxyStore } from "@/stores/exportToAnotherGalaxyStore";
import { copy as sendToClipboard } from "@/utils/clipboard";
import { absPath } from "@/utils/redirect";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const POLL_DELAY = 3000;
// Well inside the shortest storage duration a server is likely to use, so a reused link still works.
const REUSE_FOR_MS = 60 * 60 * 1000;

const store = useExportToAnotherGalaxyStore();
const { item } = storeToRefs(store);

// The export task's own state, not the storage's: a failed export still marks its storage ready.
const { waitForTask, stopWaitingForTask, isCompleted, hasFailed, failureReason, requestHasFailed } = useTaskMonitor();
const { getDownloadObjectUrl } = useShortTermStorage();
const { trackDownloadRequestWithData } = useDownloadTracker();

// This dialog lives as long as the page, so reopening an item shows its export again.
const preparedExports = new Map<string, { storageRequestId: string; taskId: string; startedAt: number }>();
const trackedExports = new Map<string, MonitoringData>();

const storageRequestId = ref<string>();
const startError = ref<string>();

const showDialog = computed({
    get: () => Boolean(item.value),
    set: (show: boolean) => {
        if (!show) {
            store.close();
        }
    },
});
const noun = computed(() => (item.value?.contentType === "dataset_collection" ? "collection" : "dataset"));
const link = computed(() =>
    isCompleted.value && storageRequestId.value ? absPath(getDownloadObjectUrl(storageRequestId.value)) : undefined,
);
const errorMessage = computed(() => {
    if (startError.value) {
        return startError.value;
    }
    // Until the new export has started, the monitor may still hold the previous one's state.
    if (!storageRequestId.value) {
        return undefined;
    }
    if (hasFailed.value) {
        return failureReason.value || "The export failed.";
    }
    return requestHasFailed.value ? "Galaxy could not say how the export is going. Please try again later." : undefined;
});

// Dataset and collection ids can be equal, so the type is part of the key.
function keyOf(exportable: ExportableItem) {
    return `${exportable.contentType}:${exportable.contentId}`;
}

// Recent Exports only learns from the storage, which a failed export also marks ready, so tell it the outcome.
function finishTracking(exportable: ExportableItem, status: Pick<MonitoringData, "taskStatus" | "failureReason">) {
    const tracked = trackedExports.get(keyOf(exportable));
    if (tracked) {
        trackDownloadRequestWithData({ ...tracked, ...status, isFinal: true });
    }
}

watch(isCompleted, (completed) => {
    if (completed && item.value) {
        finishTracking(item.value, { taskStatus: READY_STATE });
    }
});

watch([hasFailed, failureReason], ([failed]) => {
    if (failed && item.value) {
        preparedExports.delete(keyOf(item.value));
        // Any state but ready or pending reads as failed there.
        finishTracking(item.value, { taskStatus: "FAILURE", failureReason: failureReason.value });
    }
});

watch(item, (exportable) => {
    stopWaitingForTask();
    storageRequestId.value = undefined;
    startError.value = undefined;
    if (exportable) {
        startExport(exportable);
    }
});

function isShown(key: string) {
    return item.value !== null && keyOf(item.value) === key;
}

async function prepareExport(exportable: ExportableItem) {
    const { data, error } = await GalaxyApi().POST(
        "/api/histories/{history_id}/contents/{type}s/{id}/prepare_store_download",
        {
            params: {
                path: { history_id: exportable.historyId, type: exportable.contentType, id: exportable.contentId },
            },
            body: { model_store_format: "tar.gz", include_files: true, include_deleted: false, include_hidden: false },
        },
    );
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

async function startExport(exportable: ExportableItem) {
    const key = keyOf(exportable);
    const prepared = preparedExports.get(key);
    if (prepared && Date.now() - prepared.startedAt < REUSE_FOR_MS) {
        storageRequestId.value = prepared.storageRequestId;
        waitForTask(prepared.taskId, POLL_DELAY);
        return;
    }
    let data;
    try {
        data = await prepareExport(exportable);
    } catch (e) {
        if (isShown(key)) {
            startError.value = errorMessageAsString(e);
        }
        return;
    }
    preparedExports.set(key, {
        storageRequestId: data.storage_request_id,
        taskId: data.task.id,
        startedAt: Date.now(),
    });
    const tracked: MonitoringData = {
        taskId: data.storage_request_id,
        taskType: "short_term_storage",
        request: {
            source: "history-content-export",
            taskType: "short_term_storage",
            action: "export",
            object: {
                id: exportable.contentId,
                type: exportable.contentType === "dataset_collection" ? "collection" : "dataset",
                name: exportable.contentName,
            },
            description: `Export of ${exportable.contentName} for another Galaxy`,
        },
        startedAt: new Date(),
        isFinal: false,
    };
    trackedExports.set(key, tracked);
    trackDownloadRequestWithData(tracked);
    // The dialog may have been closed or opened for another item while the request was on its way.
    if (isShown(key)) {
        storageRequestId.value = data.storage_request_id;
        waitForTask(data.task.id, POLL_DELAY);
    }
}

onUnmounted(stopWaitingForTask);
</script>

<template>
    <GModal v-model:show="showDialog" title="Export to another Galaxy" size="small">
        <GAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</GAlert>
        <div v-else-if="link">
            <BInputGroup>
                <BFormInput
                    :value="link"
                    readonly
                    aria-label="Link for another Galaxy"
                    data-description="galaxy export link" />
                <BInputGroupAppend>
                    <GButton color="blue" @click="sendToClipboard(link, 'Link copied to your clipboard')">
                        <FontAwesomeIcon :icon="faCopy" />
                        Copy
                    </GButton>
                </BInputGroupAppend>
            </BInputGroup>
            <p class="mt-2">
                Anyone with this link can download this {{ noun }} without logging in, until the link expires (usually
                after 24 hours). It can't be withdrawn before then.
            </p>
            <p>
                On the other Galaxy, open Upload and choose <b>Import from Another Galaxy</b>. Your exports are also
                listed under <router-link to="/downloads" @click="showDialog = false">Recent Exports</router-link>.
            </p>
        </div>
        <LoadingSpan v-else message="Preparing the export" />
    </GModal>
</template>
