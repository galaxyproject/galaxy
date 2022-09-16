<script setup>
import { watch } from "vue";
import { BButton } from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCloudUploadAlt, faSpinner, faCheckCircle, faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { useTaskMonitor } from "composables/useTaskMonitor";
library.add(faCloudUploadAlt, faSpinner, faCheckCircle, faExclamationCircle);

const { isRunning, isCompleted, hasFailed, requestHasFailed, waitForTask } = useTaskMonitor();

const props = defineProps({
    title: { type: String, required: true },
    taskId: { type: String, default: null },
});

const emit = defineEmits(["onClick"]);

watch(
    () => props.taskId,
    (newTaskId, oldTaskId) => {
        if (newTaskId !== oldTaskId) {
            waitForTask(newTaskId);
        }
    }
);
</script>

<template>
    <div>
        <b-button v-b-tooltip.hover.bottom :title="props.title" @click="() => emit('onClick')">
            <font-awesome-icon v-if="isRunning" icon="spinner" spin />
            <font-awesome-icon v-else-if="hasFailed || requestHasFailed" icon="exclamation-circle" />
            <font-awesome-icon v-else-if="isCompleted" icon="check-circle" />
            <font-awesome-icon v-else icon="cloud-upload-alt" />
        </b-button>
    </div>
</template>
