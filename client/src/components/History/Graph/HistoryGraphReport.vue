<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed } from "vue";

import { useMarkdown } from "@/composables/markdown";

import { useHistoryGraphSummary } from "./useHistoryGraphSummary";

import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    historyId: string;
}

const props = defineProps<Props>();

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });
const { loading, error, summary } = useHistoryGraphSummary(props.historyId);

const summaryHtml = computed(() => (summary.value ? renderMarkdown(summary.value) : ""));
</script>

<template>
    <div class="history-graph-report p-2">
        <LoadingSpan v-if="loading" message="Generating history summary" />
        <BAlert v-else-if="error" variant="danger" show class="mb-0">
            Failed to generate the AI summary: {{ error }}
        </BAlert>
        <!-- eslint-disable-next-line vue/no-v-html — markdown is sanitised by useMarkdown -->
        <div v-else-if="summary" class="report-text" v-html="summaryHtml" />
        <BAlert v-else show variant="info" class="mb-0">No summary available.</BAlert>
    </div>
</template>

<style lang="scss" scoped>
.report-text {
    font-size: 0.9rem;
    line-height: 1.4;

    :deep(h2) {
        font-size: 1rem;
        font-weight: 600;
        margin-top: 0.75rem;
        margin-bottom: 0.25rem;
    }
    :deep(p) {
        margin-bottom: 0.5rem;
    }
    :deep(ul),
    :deep(ol) {
        margin-bottom: 0.5rem;
        padding-left: 1.25rem;
    }
    :deep(code) {
        font-size: 0.85em;
    }
}
</style>
