<script setup lang="ts">
import { computed } from "vue";

import { InvocationJobsSummary } from "@/api/invocations";

import {
    errorCount as jobStatesSummaryErrorCount,
    jobCount as jobStatesSummaryJobCount,
    numTerminal,
    okCount as jobStatesSummaryOkCount,
    runningCount as jobStatesSummaryRunningCount,
} from "./util";

import ProgressBar from "@/components/ProgressBar.vue";

interface Props {
    jobStatesSummary: InvocationJobsSummary;
    invocationSchedulingTerminal: boolean;
    invocationAndJobTerminal: boolean;
}

const props = defineProps<Props>();

const jobCount = computed<number>(() => {
    return jobStatesSummaryJobCount(props.jobStatesSummary);
});

const okCount = computed<number>(() => {
    return jobStatesSummaryOkCount(props.jobStatesSummary);
});

const runningCount = computed<number>(() => {
    return jobStatesSummaryRunningCount(props.jobStatesSummary);
});

const errorCount = computed<number>(() => {
    return jobStatesSummaryErrorCount(props.jobStatesSummary);
});

const newCount = computed<number>(() => {
    return jobCount.value - okCount.value - runningCount.value - errorCount.value;
});

const jobStatesStr = computed(() => {
    let jobStr = `${numTerminal(props.jobStatesSummary) || 0} of ${jobCount.value} jobs complete`;
    if (!props.invocationSchedulingTerminal) {
        jobStr += " (total number of jobs will change until all steps fully scheduled)";
    }
    return `${jobStr}.`;
});
</script>

<template>
    <ProgressBar
        :note="jobStatesStr"
        :total="jobCount"
        :ok-count="okCount"
        :running-count="runningCount"
        :new-count="newCount"
        :error-count="errorCount"
        :loading="!invocationAndJobTerminal"
        class="jobs-progress" />
</template>
