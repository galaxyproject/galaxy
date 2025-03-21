<script setup lang="ts">
import { BCard } from "bootstrap-vue";
import { computed, ref } from "vue";

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
    description: `正在将调用 ${props.invocationId} 导出到短期存储以准备下载`,
}));

const exportToRemoteRequest = computed<MonitoringRequest>(() => ({
    source: monitoringSource,
    action: "export",
    taskType: "task",
    object: {
        id: props.invocationId,
        type: "invocation",
    },
    description: `正在将调用 ${props.invocationId} 导出到远程源`,
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

updateExistingExportProgress();

defineExpose({
    updateExistingExportProgress,
});
</script>

<template>
    <BCard v-show="hasExistingStsExportData || hasExistingRemoteExportData" class="mb-2">
        <h2>这是您最新的导出请求：</h2>
        <PersistentTaskProgressMonitorAlert
            class="sts-export-monitor"
            :monitor-request="exportToStsRequest"
            :use-monitor="useStsMonitor"
            :task-id="exportToStsRequestId"
            :enable-auto-download="true"
            in-progress-message="正在准备您的导出包。请稍候..."
            completed-message="您的导出已准备好！它将很快开始下载。如果没有自动开始..."
            failed-message="您的导出失败了。"
            request-failed-message="检查导出进度失败。请稍后再试。"
            @onDismiss="dismissStsExport" />

        <PersistentTaskProgressMonitorAlert
            class="task-export-monitor"
            :monitor-request="exportToRemoteRequest"
            :use-monitor="useRemoteMonitor"
            :task-id="exportToRemoteTaskId"
            in-progress-message="正在导出到远程源。这可能需要一段时间..."
            completed-message="导出到远程源已完成！"
            failed-message="导出到远程源失败了。"
            request-failed-message="检查导出进度失败。请稍后再试。"
            @onDismiss="dismissRemoteExport" />
    </BCard>
</template>
