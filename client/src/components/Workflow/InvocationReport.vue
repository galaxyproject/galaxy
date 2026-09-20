<script setup lang="ts">
import { faEdit, faFileContract } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, provide, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { fetchInvocationReport } from "@/api/invocations";
import { useConfig } from "@/composables/config";
import { useConfirmDialog } from "@/composables/confirmDialog.js";
import { useToast } from "@/composables/toast";
import { usePageEditorStore } from "@/stores/pageEditorStore.js";
import { errorMessageAsString } from "@/utils/simple-error.js";

import GButton from "../BaseComponents/GButton.vue";
import HelpText from "../Help/HelpText.vue";
import Markdown from "@/components/Markdown/Markdown.vue";

const props = defineProps<{
    invocationId: string;
    /** Whether to enforce displaying a "Runtime Report" heading with help text */
    fromRuntimeReport?: boolean;
    historyId?: string;
}>();

const { config, isConfigLoaded } = useConfig(true);

const { confirm } = useConfirmDialog();

const Toast = useToast();

const router = useRouter();

const pageEditorStore = usePageEditorStore();
const { isLoadingPage } = storeToRefs(pageEditorStore);

const markdownConfig = ref({});
const isCreatingReport = ref(false);

const exportUrl = computed(() => `/api/invocations/${props.invocationId}/report.pdf`);

const editButtonConfig = computed(() => ({
    tooltip: "Click to create an editable report from this invocation's Runtime Report",
    label: "Edit",
    disabled: isLoadingPage.value,
}));

fetchReport();

async function fetchReport() {
    try {
        const data = await fetchInvocationReport(props.invocationId);
        markdownConfig.value = data;
    } catch (error) {
        Toast.error("Failed to load invocation report.");
    }
}

async function onEdit() {
    if (props.historyId) {
        isCreatingReport.value = true;
        try {
            const confirmed = await confirm(
                "Are you sure you want to create a new Invocation Report? This report will have context of the history and invocation that created the Runtime Report.",
                {
                    title: "Create a new Invocation Report?",
                    okText: "Create Report",
                    okIcon: faEdit,
                },
            );
            if (!confirmed) {
                return;
            }

            pageEditorStore.setCurrentContext(props.historyId, props.invocationId);
            const page = await pageEditorStore.createPage();
            if (page) {
                const editUrl =
                    `/histories/${props.historyId}/pages/${page.id}` +
                    (props.invocationId ? `?invocation_id=${props.invocationId}` : "");
                router.push(editUrl);
            } else {
                pageEditorStore.clearCurrentPage();
            }
        } catch (error) {
            Toast.error(errorMessageAsString(error), "Failed to create a Galaxy Notebook");
        } finally {
            isCreatingReport.value = false;
        }
    } else {
        router.push(`/pages/create?invocation_id=${props.invocationId}`);
    }
}

// Provide invocationId to all descendant components for inline directive resolution
provide("invocationId", props.invocationId);
</script>

<template>
    <Markdown
        v-if="isConfigLoaded"
        :markdown-config="markdownConfig"
        :edit-button-config="editButtonConfig"
        :enable_beta_markdown_export="config.enable_beta_markdown_export"
        :export-link="exportUrl"
        :download-endpoint="exportUrl"
        direct-download-link
        @onEdit="onEdit">
        <template v-if="props.fromRuntimeReport" v-slot:heading>
            Runtime Report
            <HelpText uri="galaxy.invocations.reports.runtimeReport" info-icon />
        </template>

        <template v-slot:extra-actions>
            <GButton
                size="small"
                tooltip
                title="Click to view existing/edited reports for this workflow invocation"
                outline
                color="blue"
                @click="router.push(`/workflows/invocations/${props.invocationId}/reports`)">
                View Existing Reports
                <FontAwesomeIcon :icon="faFileContract" />
            </GButton>
        </template>
    </Markdown>
</template>
