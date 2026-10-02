<script setup lang="ts">
import { faExchangeAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, onUnmounted, ref } from "vue";

import { GalaxyApi } from "@/api";
import { useConfig } from "@/composables/config";
import { useShortTermStorage } from "@/composables/shortTermStorage";
import { useTaskMonitor } from "@/composables/taskMonitor";
import { copy as sendToClipboard } from "@/utils/clipboard";
import { absPath } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

const props = defineProps<{
    historyId: string;
    contentType: "dataset" | "dataset_collection";
    contentId: string;
    label?: string;
}>();

// The export task's own state, not the storage's: a failed export still marks its storage ready.
const { waitForTask, stopWaitingForTask, isRunning, isCompleted, hasFailed, failureReason, requestHasFailed } =
    useTaskMonitor();
const { getDownloadObjectUrl } = useShortTermStorage();
const { config } = useConfig(true);
const showDialog = ref(false);
const isStarting = ref(false);
const storageRequestId = ref<string>();
const startError = ref<string>();

const link = computed(() =>
    isCompleted.value && storageRequestId.value ? absPath(getDownloadObjectUrl(storageRequestId.value)) : undefined,
);
const errorMessage = computed(() => {
    if (startError.value) {
        return startError.value;
    }
    if (hasFailed.value) {
        return failureReason.value || "The link could not be prepared.";
    }
    return requestHasFailed.value ? "The link could not be prepared." : undefined;
});

async function onExport() {
    showDialog.value = true;
    // Each export archives every file again, so reopen the link while it is still good.
    if (isStarting.value || isRunning.value || link.value) {
        return;
    }
    isStarting.value = true;
    startError.value = undefined;
    storageRequestId.value = undefined;
    const { data, error } = await GalaxyApi().POST(
        "/api/histories/{history_id}/contents/{type}s/{id}/prepare_store_download",
        {
            params: { path: { history_id: props.historyId, type: props.contentType, id: props.contentId } },
            body: { model_store_format: "tar.gz", include_files: true, include_deleted: false, include_hidden: false },
        },
    );
    isStarting.value = false;
    if (error) {
        startError.value = errorMessageAsString(error);
        return;
    }
    storageRequestId.value = data.storage_request_id;
    waitForTask(data.task.id, 3000);
}

onUnmounted(stopWaitingForTask);
</script>

<template>
    <span v-if="config.enable_celery_tasks" class="export-for-galaxy-link">
        <GButton
            class="px-1"
            title="Link for another Galaxy"
            size="small"
            :color="props.label ? 'blue' : undefined"
            transparent
            data-description="export for galaxy link"
            @click.stop="onExport">
            <FontAwesomeIcon fixed-width :icon="faExchangeAlt" />
            <span v-if="props.label">{{ props.label }}</span>
        </GButton>
        <GModal :show.sync="showDialog" title="Link for another Galaxy" size="small">
            <p v-if="errorMessage" class="text-danger">{{ errorMessage }}</p>
            <div v-else-if="link">
                <input class="form-control" :value="link" readonly data-description="galaxy link" />
                <GButton class="mt-2" size="small" @click="sendToClipboard(link, 'Link copied')">Copy link</GButton>
                <p class="mt-2">
                    Anyone with this link can download this item for a limited time. On the other Galaxy, paste it into
                    Upload, Import from Another Galaxy.
                </p>
            </div>
            <p v-else>Preparing the link...</p>
        </GModal>
    </span>
</template>
