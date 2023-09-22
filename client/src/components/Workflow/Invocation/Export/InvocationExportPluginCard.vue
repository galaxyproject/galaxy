<script setup>
import { computed, ref, provide } from "vue";
import { BCard, BCardTitle, BButtonToolbar, BButtonGroup } from "bootstrap-vue";
import { InvocationExportPlugin } from "./model";
import ActionButton from "./ActionButton.vue";
import StsDownloadButton from "components/StsDownloadButton.vue";
import ExportToRemoteButton from "components/Workflow/Invocation/Export/ExportToRemoteButton.vue";
import ExportToRemoteModal from "components/Workflow/Invocation/Export/ExportToRemoteModal.vue";
import { useMarkdown } from "composables/markdown";
import { Toast } from "composables/toast";
import axios from "axios";

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const exportRemoteModal = ref(null);
const exportToRemoteTaskId = ref(null);

const props = defineProps({
    exportPlugin: { type: InvocationExportPlugin, required: true },
    invocationId: { type: String, required: true },
});

// Make `invocationId` available to child components via `inject`
provide("invocationId", props.invocationId);

const descriptionRendered = computed(() => renderMarkdown(props.exportPlugin.markdownDescription));
const invocationDownloadUrl = computed(() => `/api/invocations/${props.invocationId}/prepare_store_download`);
const downloadParams = computed(() => {
    const exportParams = props.exportPlugin.exportParams;
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

function exportToFileSource(exportDirectory, fileName) {
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
    exportRemoteModal.value.hideModal();
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
        <b-card class="export-plugin-card mb-1">
            <b-card-title class="export-plugin-title align-items-center d-flex justify-content-between">
                {{ exportPlugin.title }}
                <b-button-toolbar aria-label="Export Options">
                    <b-button-group>
                        <sts-download-button
                            :title="'Download Invocation as ' + exportPlugin.title"
                            :download-endpoint="invocationDownloadUrl"
                            :post-parameters="downloadParams"
                            class="download-button" />
                        <export-to-remote-button
                            :title="'Export Invocation as ' + exportPlugin.title + ' and upload to remote source'"
                            :task-id="exportToRemoteTaskId"
                            class="remote-export-button"
                            @onClick="openRemoteExportDialog"
                            @onSuccess="onExportToFileSourceSuccess"
                            @onFailure="onExportToFileSourceFailure" />
                        <action-button
                            v-for="action in exportPlugin.additionalActions"
                            :key="action.id"
                            :action="action"
                            class="action-button" />
                    </b-button-group>
                </b-button-toolbar>
            </b-card-title>

            <div class="markdown-description" v-html="descriptionRendered" />
        </b-card>
        <export-to-remote-modal
            ref="exportRemoteModal"
            :invocation-id="props.invocationId"
            :export-plugin="props.exportPlugin"
            @onExportToFileSource="exportToFileSource" />
    </div>
</template>
