<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCloudUploadAlt, faDownload } from "@fortawesome/free-solid-svg-icons";
import axios from "axios";
import { BButtonGroup, BButtonToolbar, BCard, BCardTitle } from "bootstrap-vue";
import { computed, provide, ref } from "vue";

import { useMarkdown } from "@/composables/markdown";
import { type MonitoringRequest } from "@/composables/persistentProgressMonitor";
import { useShortTermStorageMonitor } from "@/composables/shortTermStorageMonitor";
import { useTaskMonitor } from "@/composables/taskMonitor";
import { Toast } from "@/composables/toast";

import { type InvocationExportPlugin } from "./model";

import ActionButton from "./ActionButton.vue";
import PersistentTaskProgressMonitorAlert from "@/components/Common/PersistentTaskProgressMonitorAlert.vue";
import ExportButton from "@/components/Workflow/Invocation/Export/ExportButton.vue";
import ExportToRemoteModal from "@/components/Workflow/Invocation/Export/ExportToRemoteModal.vue";

library.add(faCloudUploadAlt, faDownload);

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const exportRemoteModal = ref();
const exportToRemoteTaskId = ref();
const exportToStsRequestId = ref();

interface Props {
    exportPlugin: InvocationExportPlugin;
    invocationId: string;
}

const taskMonitor = useTaskMonitor();
const stsMonitor = useShortTermStorageMonitor();

const props = defineProps<Props>();

// Make `invocationId` available to child components via `inject`
provide("invocationId", props.invocationId);

const descriptionRendered = computed(() => renderMarkdown(props.exportPlugin.markdownDescription));
const preparedDownloadUrl = computed(() => `/api/invocations/${props.invocationId}/prepare_store_download`);
const downloadParams = computed(() => {
    const exportParams = props.exportPlugin.exportParams;
    if (!exportParams) {
        return undefined;
    }
    return {
        model_store_format: exportParams.modelStoreFormat,
        include_files: exportParams.includeFiles,
        include_deleted: exportParams.includeDeleted,
        include_hidden: exportParams.includeHidden,
    };
});

const exportToStsRequest = computed<MonitoringRequest>(() => ({
    source: props.exportPlugin.id,
    action: "export",
    taskType: "short_term_storage",
    object: {
        id: props.invocationId,
        type: "invocation",
    },
    description: `Exporting invocation ${props.invocationId} to Short Term Storage in preparation for download`,
}));

const exportToRemoteRequest = computed<MonitoringRequest>(() => ({
    source: props.exportPlugin.id,
    action: "export",
    taskType: "task",
    object: {
        id: props.invocationId,
        type: "invocation",
    },
    description: `Exporting invocation ${props.invocationId} to remote source`,
}));

function openRemoteExportDialog() {
    exportRemoteModal.value.showModal();
}

function closeRemoteExportDialog() {
    exportRemoteModal.value.hideModal();
}

async function exportToSts() {
    try {
        const response = await axios.post(preparedDownloadUrl.value, downloadParams.value);
        exportToStsRequestId.value = response.data.storage_request_id;
    } catch (err) {
        Toast.error(`Failed to export invocation. ${err}`);
    }
}

function exportToFileSource(exportDirectory: string, fileName: string) {
    if (!props.exportPlugin.exportParams) {
        throw new Error("Export parameters are not defined");
    }
    const exportFormat = props.exportPlugin.exportParams.modelStoreFormat;
    const exportDirectoryUri = `${exportDirectory}/${fileName}.${exportFormat}`;
    const writeStoreParams = {
        target_uri: exportDirectoryUri,
        ...downloadParams.value,
    };
    axios
        .post(`/api/invocations/${props.invocationId}/write_store`, writeStoreParams)
        .then((response) => {
            exportToRemoteTaskId.value = response.data.id;
        })
        .catch((err) => {
            Toast.error(`Failed to export to remote source. ${err}`);
        });
    closeRemoteExportDialog();
}
</script>

<template>
    <div>
        <BCard class="export-plugin-card mb-1">
            <BCardTitle class="export-plugin-title align-items-center d-flex justify-content-between">
                {{ exportPlugin.title }}
                <BButtonToolbar aria-label="Export Options">
                    <BButtonGroup>
                        <ExportButton
                            :title="`Download Invocation as ${exportPlugin.title}`"
                            :idle-icon="faDownload"
                            :is-busy="stsMonitor.isRunning.value"
                            class="download-button"
                            @onClick="exportToSts">
                        </ExportButton>
                        <ExportButton
                            :title="`Export Invocation as ${exportPlugin.title} and upload to Remote Source`"
                            :idle-icon="faCloudUploadAlt"
                            :is-busy="taskMonitor.isRunning.value"
                            class="remote-export-button"
                            @onClick="openRemoteExportDialog" />
                        <ActionButton
                            v-for="action in exportPlugin.additionalActions"
                            :key="action.id"
                            :action="action"
                            class="action-button" />
                    </BButtonGroup>
                </BButtonToolbar>
            </BCardTitle>

            <div class="markdown-description" v-html="descriptionRendered" />

            <PersistentTaskProgressMonitorAlert
                class="sts-export-monitor"
                :monitor-request="exportToStsRequest"
                :use-monitor="stsMonitor"
                :task-id="exportToStsRequestId"
                :enable-auto-download="true"
                in-progress-message="Preparing your export package. Please wait..."
                completed-message="Your export is ready! It will start downloading shortly. If it does not start automatically..."
                failed-message="Your export has failed."
                request-failed-message="Failed to check export progress. Try again later." />

            <PersistentTaskProgressMonitorAlert
                class="task-export-monitor"
                :monitor-request="exportToRemoteRequest"
                :use-monitor="taskMonitor"
                :task-id="exportToRemoteTaskId"
                in-progress-message="Exporting to remote source. It may take a while..."
                completed-message="Export to remote source is complete!"
                failed-message="Export to remote source has failed."
                request-failed-message="Failed to check export progress. Try again later." />
        </BCard>
        <ExportToRemoteModal
            ref="exportRemoteModal"
            :invocation-id="props.invocationId"
            :export-plugin="props.exportPlugin"
            @onExportToFileSource="exportToFileSource" />
    </div>
</template>
