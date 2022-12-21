<script setup>
import { watch } from "vue";
import { BButton } from "bootstrap-vue";
import { useTaskMonitor } from "composables/taskMonitor";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const { isRunning, isCompleted, hasFailed, requestHasFailed, waitForTask } = useTaskMonitor();

const props = defineProps({
    title: { type: String, required: true },
    taskId: { type: String, default: null },
});

const emit = defineEmits(["onClick", "onSuccess", "onFailure"]);

watch(
    () => props.taskId,
    (newTaskId, oldTaskId) => {
        if (newTaskId !== oldTaskId) {
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

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCloudUploadAlt, faSpinner, faCheckCircle, faExclamationCircle } from "@fortawesome/free-solid-svg-icons";

library.add(faCloudUploadAlt, faSpinner, faCheckCircle, faExclamationCircle);
</script>

<template>
    <b-button v-b-tooltip.hover.bottom :title="props.title" @click="() => emit('onClick')">
        <font-awesome-icon v-if="isRunning" icon="spinner" spin />
        <font-awesome-icon v-else-if="hasFailed || requestHasFailed" icon="exclamation-circle" />
        <font-awesome-icon v-else-if="isCompleted" icon="check-circle" />
        <font-awesome-icon v-else icon="cloud-upload-alt" />
    </b-button>
</template>
