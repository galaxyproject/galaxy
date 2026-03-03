<script setup lang="ts">
import { faMagic, faSpinner, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, provide, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { generateAIInvocationReport } from "@/api/chat";
import { fetchInvocationReport } from "@/api/invocations";
import { useConfig } from "@/composables/config";
import { useToast } from "@/composables/toast";

import GButton from "../BaseComponents/GButton.vue";
import Markdown from "@/components/Markdown/Markdown.vue";

const props = defineProps<{
    invocationId: string;
}>();

const { config, isConfigLoaded } = useConfig(true);

const Toast = useToast();

const router = useRouter();

const markdownConfig = ref({});
const invocationMarkdown = ref<string | null>(null);
const aiReportGenerated = ref(false);
const aiReportLoading = ref(false);

const exportUrl = computed(() => `/api/invocations/${props.invocationId}/report.pdf`);

fetchReport();

async function fetchReport() {
    try {
        const data = await fetchInvocationReport(props.invocationId);
        markdownConfig.value = data;
        invocationMarkdown.value = data.markdown || null;
    } catch (error) {
        Toast.error("Failed to load invocation report.");
    }
}

async function generateAIReport() {
    try {
        aiReportLoading.value = true;
        const { model, report, total_tokens } = await generateAIInvocationReport(props.invocationId);
        Toast.success(
            `Report generated using ${model}${total_tokens ? `, total tokens used: ${total_tokens}` : ""}.`,
            "AI Report generated successfully.",
        );

        (markdownConfig.value as any).markdown = report;
        aiReportGenerated.value = true;
    } catch (error) {
        Toast.error("Failed to generate AI report.");
    } finally {
        aiReportLoading.value = false;
    }
}

function onEdit() {
    router.push(`/pages/create?invocation_id=${props.invocationId}`);
}

function resetAIReport() {
    (markdownConfig.value as any).markdown = invocationMarkdown.value;
    aiReportGenerated.value = false;
}

// Provide invocationId to all descendant components for inline directive resolution
provide("invocationId", props.invocationId);
</script>

<template>
    <Markdown
        v-if="isConfigLoaded"
        :key="aiReportGenerated"
        :markdown-config="markdownConfig"
        :enable_beta_markdown_export="config.enable_beta_markdown_export"
        :export-link="exportUrl"
        :download-endpoint="exportUrl"
        direct-download-link
        @onEdit="onEdit">
        <template v-slot:extra-actions>
            <GButton
                v-if="!aiReportGenerated && !aiReportLoading"
                tooltip
                title="Generate AI ChatGXY report based on the workflow and its results"
                size="small"
                color="blue"
                outline
                @click="generateAIReport">
                AI Report
                <FontAwesomeIcon :icon="faMagic" />
            </GButton>
            <GButton
                v-else
                tooltip
                :title="aiReportLoading ? 'Generating AI report...' : 'Reset to original report'"
                size="small"
                color="blue"
                outline
                :disabled="aiReportLoading"
                @click="resetAIReport">
                Reset
                <FontAwesomeIcon :icon="aiReportLoading ? faSpinner : faUndo" :spin="aiReportLoading" />
            </GButton>
        </template>
    </Markdown>
</template>
