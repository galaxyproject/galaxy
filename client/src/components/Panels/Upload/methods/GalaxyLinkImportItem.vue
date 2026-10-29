<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

import { GalaxyApi } from "@/api";
import { useTaskMonitor } from "@/composables/taskMonitor";
import { errorMessageAsString } from "@/utils/simple-error";

import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    /**
     * History the item is imported into
     */
    historyId: string;
    /**
     * Short term storage link of the item on the other Galaxy
     */
    link: string;
    /**
     * Name of the item on the other Galaxy
     */
    name: string;
}

const props = defineProps<Props>();

const { waitForTask, stopWaitingForTask, isRunning, isCompleted, hasFailed, failureReason, requestHasFailed } =
    useTaskMonitor();

const isStarting = ref(true);
const startError = ref<string>();

async function startImport() {
    try {
        const { data, error } = await GalaxyApi().POST("/api/histories/{history_id}/contents_from_store_async", {
            params: { path: { history_id: props.historyId } },
            body: { store_content_uri: props.link, model_store_format: "tar.gz", discarded_data: "forbid" },
        });
        if (error) {
            startError.value = errorMessageAsString(error);
            return;
        }
        waitForTask(data.id, 3000);
    } catch (e) {
        startError.value = errorMessageAsString(e, "The import could not be started.");
    } finally {
        isStarting.value = false;
    }
}

onMounted(startImport);

onUnmounted(stopWaitingForTask);
</script>

<template>
    <li class="galaxy-link-import-item mb-2" data-description="galaxy picker import item">
        <b>{{ props.name || "Unnamed item" }}</b>
        <LoadingSpan v-if="isStarting || isRunning" message="Importing" />
        <span v-else-if="startError" class="text-danger">{{ startError }}</span>
        <span v-else-if="hasFailed" class="text-danger">
            Could not be imported. The link may have expired.
            <span v-if="failureReason">{{ failureReason }}</span>
        </span>
        <span v-else-if="requestHasFailed" class="text-warning">
            Galaxy could not check how the import is going. It may still finish, so look at the history.
        </span>
        <span v-else-if="isCompleted" class="text-success">Imported</span>
    </li>
</template>
