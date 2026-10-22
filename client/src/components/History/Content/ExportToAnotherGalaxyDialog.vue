<script setup lang="ts">
import { faCopy } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormInput, BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onUnmounted, ref, shallowReactive, watch } from "vue";

import { GalaxyApi } from "@/api";
import { useDownloadTracker } from "@/composables/downloadTracker";
import type { TaskMonitor } from "@/composables/genericTaskMonitor";
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

interface Export {
    storageRequestId: string;
    taskId: string;
    startedAt: number;
    monitor: TaskMonitor;
}

const store = useExportToAnotherGalaxyStore();
const { item } = storeToRefs(store);

const { getDownloadObjectUrl } = useShortTermStorage();
const { trackDownloadRequestWithData } = useDownloadTracker();

// This dialog lives as long as the page. Each export has its own monitor, so it is followed to its end even
// after the dialog closes, and reopening an item shows its export again.
const exports = shallowReactive(new Map<string, Export>());
// Items whose export request has not come back yet, so reopening one does not start a second export.
const starting = new Set<string>();

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
const shown = computed(() => (item.value ? exports.get(keyOf(item.value)) : undefined));
// The export task's own state, not the storage's: a failed export still marks its storage ready.
const link = computed(() =>
    shown.value?.monitor.isCompleted.value ? absPath(getDownloadObjectUrl(shown.value.storageRequestId)) : undefined,
);
const errorMessage = computed(() => {
    if (startError.value) {
        return startError.value;
    }
    const monitor = shown.value?.monitor;
    if (monitor?.hasFailed.value) {
        return monitor.failureReason.value || "The export failed.";
    }
    return monitor?.requestHasFailed.value
        ? "Galaxy could not say how the export is going. Please try again later."
        : undefined;
});

// Dataset and collection ids can be equal, so the type is part of the key.
function keyOf(exportable: ExportableItem) {
    return `${exportable.contentType}:${exportable.contentId}`;
}

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

watch(item, (exportable) => {
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
    let data;
    starting.add(key);
    try {
        data = await prepareExport(exportable);
    } catch (e) {
        if (isShown(key)) {
            startError.value = errorMessageAsString(e);
        }
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
                id: exportable.contentId,
                type: exportable.contentType === "dataset_collection" ? "collection" : "dataset",
                name: exportable.contentName,
            },
            description: `Export of ${exportable.contentName} for another Galaxy`,
        },
        startedAt: new Date(),
        isFinal: false,
    };
    trackDownloadRequestWithData(tracked);
    const monitor = useTaskMonitor();
    recordOutcome(monitor, tracked);
    exports.set(key, {
        storageRequestId: data.storage_request_id,
        taskId: data.task.id,
        startedAt: Date.now(),
        monitor,
    });
    monitor.waitForTask(data.task.id, POLL_DELAY);
}

onUnmounted(() => exports.forEach((entry) => entry.monitor.stopWaitingForTask()));
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
