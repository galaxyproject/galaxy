<script setup lang="ts">
import { computed, provide, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { fetchInvocationReport } from "@/api/invocations";
import { useConfig } from "@/composables/config";
import { useToast } from "@/composables/toast";

import Markdown from "@/components/Markdown/Markdown.vue";

const props = defineProps<{
    invocationId: string;
}>();

const { config, isConfigLoaded } = useConfig(true);

const Toast = useToast();

const router = useRouter();

const markdownConfig = ref({});

const exportUrl = computed(() => `/api/invocations/${props.invocationId}/report.pdf`);

fetchReport();

async function fetchReport() {
    try {
        const data = await fetchInvocationReport(props.invocationId);
        markdownConfig.value = data;
    } catch (error) {
        Toast.error("Failed to load invocation report.");
    }
}

function onEdit() {
    router.push(`/pages/create?invocation_id=${props.invocationId}`);
}

// Provide invocationId to all descendant components for inline directive resolution
provide("invocationId", props.invocationId);
</script>

<template>
    <Markdown
        v-if="isConfigLoaded"
        :markdown-config="markdownConfig"
        :enable_beta_markdown_export="config.enable_beta_markdown_export"
        :export-link="exportUrl"
        :download-endpoint="exportUrl"
        direct-download-link
        @onEdit="onEdit" />
</template>
