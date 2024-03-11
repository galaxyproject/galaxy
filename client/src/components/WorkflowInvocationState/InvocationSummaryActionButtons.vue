<script setup lang="ts">
import { computed } from "vue";

import { getRootFromIndexLink } from "@/onload";

interface Props {
    invocationId: string;
    invocationState: string;
    invocationStateSuccess: boolean;
    runningCount: number;
}

const props = defineProps<Props>();

const reportTooltip = "View report for this workflow invocation";
const generatePdfTooltip = "Generate PDF report for this workflow invocation";

function getUrl(path: string): string {
    return getRootFromIndexLink() + path;
}

const invocationLink = computed<string | null>(() => {
    const id = props.invocationId;
    if (id) {
        return getUrl(`workflows/invocations/report?id=${id}`);
    } else {
        return null;
    }
});

const invocationPdfLink = computed<string | null>(() => {
    const id = props.invocationId;
    if (id) {
        return getUrl(`api/invocations/${id}/report.pdf`);
    } else {
        return null;
    }
});

const disabledReportTooltip = computed(() => {
    const state = props.invocationState;
    const runCount = props.runningCount;
    if (state != "scheduled") {
        return `This workflow is not currently scheduled. The current state is ${state}. Once the workflow is fully scheduled and jobs have complete this option will become available.`;
    } else if (runCount != 0) {
        return `The workflow invocation still contains ${runCount} running job(s). Once these jobs have completed this option will become available.`;
    } else {
        return "Steps for this workflow are still running. A report will be available once complete.";
    }
});
</script>

<template>
    <div>
        <span>
            <b-button
                v-b-tooltip.hover
                :title="invocationStateSuccess ? reportTooltip : disabledReportTooltip"
                :disabled="!invocationStateSuccess"
                size="sm"
                class="invocation-report-link"
                :href="invocationLink">
                View Report
            </b-button>
            <b-button
                v-b-tooltip.hover
                :title="invocationStateSuccess ? generatePdfTooltip : disabledReportTooltip"
                :disabled="!invocationStateSuccess"
                size="sm"
                class="invocation-pdf-link"
                :href="invocationPdfLink"
                target="_blank">
                Generate PDF
            </b-button>
        </span>
    </div>
</template>
