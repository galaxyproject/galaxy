<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheckCircle, faCloudUploadAlt, faExclamationCircle, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { watch } from "vue";

import { useTaskMonitor } from "@/composables/taskMonitor";

library.add(faCloudUploadAlt, faSpinner, faCheckCircle, faExclamationCircle);

const { isRunning, isCompleted, hasFailed, requestHasFailed, waitForTask } = useTaskMonitor();

interface Props {
    title: string;
    taskId?: string;
}

const props = defineProps<Props>();

const emit = defineEmits(["onClick", "onSuccess", "onFailure"]);

watch(
    () => props.taskId,
    (newTaskId, oldTaskId) => {
        if (newTaskId && newTaskId !== oldTaskId) {
            waitForTask(newTaskId);
        }
    }
);

watch([isCompleted, hasFailed, requestHasFailed], ([newIsCompleted, newHasFailed, newRequestHasFailed]) => {
    if (newIsCompleted) {
        emit("onSuccess");
    }
    if (newHasFailed || newRequestHasFailed) {
        emit("onFailure");
    }
});
</script>

<template>
    <BButton v-b-tooltip.hover.bottom :title="props.title" @click="() => emit('onClick')">
        <FontAwesomeIcon v-if="isRunning" icon="spinner" spin />
        <FontAwesomeIcon v-else-if="hasFailed || requestHasFailed" icon="exclamation-circle" />
        <FontAwesomeIcon v-else-if="isCompleted" icon="check-circle" />
        <FontAwesomeIcon v-else icon="cloud-upload-alt" />
    </BButton>
</template>
