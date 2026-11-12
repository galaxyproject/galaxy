<script setup lang="ts">
import { onUnmounted, watch } from "vue";

import { useTaskMonitor } from "@/composables/taskMonitor";

import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    /**
     * Name of the item on the other Galaxy
     */
    name: string;
    /**
     * Why the import could not be started
     * @default undefined
     */
    startError?: string;
    /**
     * Galaxy task that imports the item, once it has started
     * @default undefined
     */
    taskId?: string;
}

const props = withDefaults(defineProps<Props>(), {
    startError: undefined,
    taskId: undefined,
});

const { waitForTask, stopWaitingForTask, isRunning, isCompleted, hasFailed, failureReason, requestHasFailed } =
    useTaskMonitor();

// The parent starts the import, so showing the row again only follows the task.
watch(
    () => props.taskId,
    (taskId) => {
        if (taskId) {
            waitForTask(taskId, 3000);
        }
    },
    { immediate: true },
);

onUnmounted(stopWaitingForTask);
</script>

<template>
    <li class="galaxy-link-import-item mb-2" data-description="galaxy picker import item">
        <b>{{ props.name || "Unnamed item" }}</b>
        <span v-if="props.startError" class="text-danger">{{ props.startError }}</span>
        <LoadingSpan v-else-if="!props.taskId || isRunning" message="Importing" />
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
