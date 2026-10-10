<script setup lang="ts">
/**
 * Table Of Contents for the tool success page, allowing quick navigation to different sections.
 */

import { computed } from "vue";

import type { JobRequest, JobResponse } from "@/api/jobs";

interface TocEntry {
    id: string;
    label: string;
    /** Set when this section can be force-expanded (i.e. it's one of the collapsible ones). */
    collapsed?: boolean;
}

const props = defineProps<{
    jobResponse?: JobResponse;
    jobDef?: JobRequest;
    webhookId?: string | null;
    showRecommendation: boolean;
    /** Controls `JobInformation`'s collapse state, so its TOC entry can force it open. */
    jobInformationCollapsed: boolean;
    /** Controls `ToolSuccessOutputs`' collapse state, so its TOC entry can force it open. */
    toolSuccessOutputsCollapsed: boolean;
}>();

const emit = defineEmits<{
    (e: "update:jobInformationCollapsed", value: boolean): void;
    (e: "update:toolSuccessOutputsCollapsed", value: boolean): void;
}>();

const entries = computed<TocEntry[]>(() => {
    const list: TocEntry[] = [];
    if (props.jobResponse?.produces_entry_points) {
        list.push({ id: "tool-entry-points", label: "Interactive Tools" });
    }
    list.push({
        id: "job-execution-details",
        label: "Job Execution Details",
        collapsed: props.jobInformationCollapsed,
    });
    if (props.jobResponse && (props.jobResponse.outputs?.length || props.jobResponse.output_collections?.length)) {
        list.push({ id: "tool-run-outputs", label: "Tool Run Outputs", collapsed: props.toolSuccessOutputsCollapsed });
    }
    if (props.jobDef && props.webhookId) {
        list.push({ id: "tool-success-webhook", label: "Before You Go" });
    }
    if (props.showRecommendation && props.jobDef?.tool_id) {
        list.push({ id: "tool-recommendation", label: "Tool Recommendation" });
    }
    return list;
});

function goTo(entry: TocEntry) {
    if (entry.collapsed) {
        if (entry.id === "job-execution-details") {
            emit("update:jobInformationCollapsed", false);
        } else if (entry.id === "tool-run-outputs") {
            emit("update:toolSuccessOutputsCollapsed", false);
        }
    }
    document.getElementById(entry.id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}
</script>

<template>
    <nav v-if="entries.length > 1" class="toc-strip" aria-label="Jump to section">
        <button v-for="entry in entries" :key="entry.id" type="button" class="toc-link" @click="goTo(entry)">
            {{ entry.label }}
        </button>
    </nav>
</template>

<style scoped lang="scss">
.toc-strip {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem;
    margin-bottom: 0.75rem;
}

.toc-link {
    appearance: none;
    border: 1px solid var(--color-grey-200);
    background: var(--color-blue-100);
    color: var(--color-blue-600);
    font-size: var(--font-size-small);
    font-weight: 600;
    border-radius: 999px;
    padding: 0.2rem 0.75rem;
    cursor: pointer;
    transition:
        background-color 0.15s ease,
        color 0.15s ease;

    &:hover,
    &:focus-visible {
        background: var(--color-yellow-100);
        color: var(--color-grey-700);
    }

    &:active {
        background: var(--color-yellow-200);
    }
}
</style>
