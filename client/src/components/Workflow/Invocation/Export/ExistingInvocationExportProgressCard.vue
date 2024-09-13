<script setup lang="ts">
import { BCard } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";

import type { TaskMonitor } from "@/composables/genericTaskMonitor";
import { getStoredProgressData, type MonitoringRequest } from "@/composables/persistentProgressMonitor";

import PersistentTaskProgressMonitorAlert from "@/components/Common/PersistentTaskProgressMonitorAlert.vue";

const monitoringSource = "wizard";

interface Props {
    invocationId: string;
    useStsMonitor: TaskMonitor;
    useRemoteMonitor: TaskMonitor;
    exportToRemoteTaskId?: string;
    exportToRemoteTargetUri?: string;
    exportToStsRequestId?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onDismissSts"): void;
    (e: "onDismissRemote"): void;
}>();

const hasExistingStsExportData = ref(false);
const hasExistingRemoteExportData = ref(false);

const exportToStsRequest = computed<MonitoringRequest>(() => ({
    source: monitoringSource,
    action: "export",
    taskType: "short_term_storage",
    object: {
        id: props.invocationId,
        type: "invocation",
    },
    description: `Exporting invocation ${props.invocationId} to Short Term Storage in preparation for download`,
}));

const exportToRemoteRequest = computed<MonitoringRequest>(() => ({
    source: monitoringSource,
    action: "export",
    taskType: "task",
    object: {
        id: props.invocationId,
        type: "invocation",
    },
    description: `Exporting invocation ${props.invocationId} to remote source`,
    remoteUri: props.exportToRemoteTargetUri,
}));

function updateExistingExportProgress() {
    const existingStsExportData = getStoredProgressData(exportToStsRequest.value);
    hasExistingStsExportData.value = existingStsExportData !== null;

    const existingRemoteExportData = getStoredProgressData(exportToRemoteRequest.value);
    hasExistingRemoteExportData.value = existingRemoteExportData !== null;
}

function dismissStsExport() {
    emit("onDismissSts");
    hasExistingStsExportData.value = false;
}

function dismissRemoteExport() {
    emit("onDismissRemote");
    hasExistingRemoteExportData.value = false;
}

onMounted(() => {
    updateExistingExportProgress();
});

defineExpose({
    updateExistingExportProgress,
});
</script>

<template>
    <BCard v-show="hasExistingStsExportData || hasExistingRemoteExportData">
        <h2>Here is your latest export request:</h2>
        <PersistentTaskProgressMonitorAlert
            class="sts-export-monitor"
            :monitor-request="exportToStsRequest"
            :use-monitor="useStsMonitor"
            :task-id="exportToStsRequestId"
            :enable-auto-download="true"
            in-progress-message="Preparing your export package. Please wait..."
            completed-message="Your export is ready! It will start downloading shortly. If it does not start automatically..."
            failed-message="Your export has failed."
            request-failed-message="Failed to check export progress. Try again later."
            @onDismiss="dismissStsExport" />

        <PersistentTaskProgressMonitorAlert
            class="task-export-monitor"
            :monitor-request="exportToRemoteRequest"
            :use-monitor="useRemoteMonitor"
            :task-id="exportToRemoteTaskId"
            in-progress-message="Exporting to remote source. It may take a while..."
            completed-message="Export to remote source is complete!"
            failed-message="Export to remote source has failed."
            request-failed-message="Failed to check export progress. Try again later."
            @onDismiss="dismissRemoteExport" />
    </BCard>
</template>
