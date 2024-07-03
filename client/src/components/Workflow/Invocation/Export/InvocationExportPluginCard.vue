<script setup lang="ts">
import axios from "axios";
import { BButtonGroup, BButtonToolbar, BCard, BCardTitle } from "bootstrap-vue";
import { computed, provide, ref } from "vue";

import { useMarkdown } from "@/composables/markdown";
import { Toast } from "@/composables/toast";

import { InvocationExportPlugin } from "./model";

import ActionButton from "./ActionButton.vue";
import StsDownloadButton from "@/components/StsDownloadButton.vue";
import ExportToRemoteButton from "@/components/Workflow/Invocation/Export/ExportToRemoteButton.vue";
import ExportToRemoteModal from "@/components/Workflow/Invocation/Export/ExportToRemoteModal.vue";

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const exportRemoteModal = ref();
const exportToRemoteTaskId = ref();

interface Props {
    exportPlugin: InvocationExportPlugin;
    invocationId: string;
}

const props = defineProps<Props>();

// Make `invocationId` available to child components via `inject`
provide("invocationId", props.invocationId);

const descriptionRendered = computed(() => renderMarkdown(props.exportPlugin.markdownDescription));
const invocationDownloadUrl = computed(() => `/api/invocations/${props.invocationId}/prepare_store_download`);
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

function openRemoteExportDialog() {
    exportRemoteModal.value.showModal();
}

function closeRemoteExportDialog() {
    exportRemoteModal.value.hideModal();
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

function onExportToFileSourceSuccess() {
    Toast.success(`Invocation successfully exported to remote source`);
}

function onExportToFileSourceFailure() {
    Toast.error(`Failed to export to remote source`);
}
</script>

<template>
    <div>
        <BCard class="export-plugin-card mb-1">
            <BCardTitle class="export-plugin-title align-items-center d-flex justify-content-between">
                {{ exportPlugin.title }}
                <BButtonToolbar aria-label="Export Options">
                    <BButtonGroup>
                        <StsDownloadButton
                            :title="'Download Invocation as ' + exportPlugin.title"
                            :download-endpoint="invocationDownloadUrl"
                            :post-parameters="downloadParams"
                            class="download-button" />
                        <ExportToRemoteButton
                            :title="'Export Invocation as ' + exportPlugin.title + ' and upload to remote source'"
                            :task-id="exportToRemoteTaskId"
                            class="remote-export-button"
                            @onClick="openRemoteExportDialog"
                            @onSuccess="onExportToFileSourceSuccess"
                            @onFailure="onExportToFileSourceFailure" />
                        <ActionButton
                            v-for="action in exportPlugin.additionalActions"
                            :key="action.id"
                            :action="action"
                            class="action-button" />
                    </BButtonGroup>
                </BButtonToolbar>
            </BCardTitle>

            <div class="markdown-description" v-html="descriptionRendered" />
        </BCard>
        <ExportToRemoteModal
            ref="exportRemoteModal"
            :invocation-id="props.invocationId"
            :export-plugin="props.exportPlugin"
            @onExportToFileSource="exportToFileSource" />
    </div>
</template>
