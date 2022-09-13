<script setup>
import { computed } from "vue";
import { BCard, BCardTitle, BButtonToolbar, BButtonGroup } from "bootstrap-vue";
import { InvocationExportPlugin } from "./model";
import StsDownloadButton from "components/StsDownloadButton.vue";
import ExportToRemoteButton from "components/Workflow/Invocation/Export/ExportToRemoteButton.vue";
import { useMarkdown } from "composables/useMarkdown";

const md = useMarkdown({ openLinksInNewPage: true });

const props = defineProps({
    exportPlugin: { type: InvocationExportPlugin, required: true },
    invocationId: { type: String, required: true },
});

const invocationDownloadUrl = computed(() => `/api/invocations/${props.invocationId}/prepare_store_download`);
const descriptionRendered = computed(() => md.render(props.exportPlugin.markdownDescription));
</script>

<template>
    <b-card class="export-plugin-card mb-1">
        <b-card-title class="align-items-center d-flex justify-content-between">
            {{ exportPlugin.title }}
            <b-button-toolbar aria-label="Export Options">
                <b-button-group>
                    <sts-download-button
                        :title="'Download Invocation as ' + exportPlugin.title"
                        :download-endpoint="invocationDownloadUrl" />
                    <export-to-remote-button
                        :title="'Export Invocation as ' + exportPlugin.title + ' and upload to remote source'" />
                </b-button-group>
            </b-button-toolbar>
        </b-card-title>

        <div v-html="descriptionRendered"></div>
    </b-card>
</template>
