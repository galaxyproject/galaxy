<script setup lang="ts">
import { computed } from "vue";

import { InvocationJobsSummary, WorkflowInvocationElementView } from "@/api/invocations";

import { runningCount as jobStatesSummaryRunningCount } from "./util";

import LoadingSpan from "@/components/LoadingSpan.vue";
import ProgressBar from "@/components/ProgressBar.vue";

import InvocationMessage from "./InvocationMessage.vue";
import InvocationSummaryActionButtons from "./InvocationSummaryActionButtons.vue";
import InvocationJobsProgressBar from "./InvocationJobsProgressBar.vue";
import InvocationStepsProgressBar from "./InvocationStepsProgressBar.vue";

interface Props {
    invocation?: WorkflowInvocationElementView;
    invocationAndJobTerminal: boolean;
    invocationSchedulingTerminal: boolean;
    jobStatesSummary: InvocationJobsSummary;
    index?: number;
}

const props = defineProps<Props>();

const invocationId = computed<string | undefined>(() => props.invocation?.id);

const indexStr = computed(() => {
    if (props.index == undefined) {
        return "";
    } else {
        return `${props.index + 1}`;
    }
});

const invocationState = computed(() => {
    return props.invocation?.state || "new";
});

const invocationStateSuccess = computed(() => {
    return invocationState.value == "scheduled" && runningCount.value === 0 && props.invocationAndJobTerminal;
});

const runningCount = computed<number>(() => {
    return jobStatesSummaryRunningCount(props.jobStatesSummary);
});

const emit = defineEmits<{
    (e: "invocation-cancelled"): void;
}>();

function onCancel() {
    emit("invocation-cancelled");
}
</script>

<template>
    <div class="mb-3 workflow-invocation-state-component">
        <InvocationSummaryActionButtons
            v-if="invocationAndJobTerminal"
            :invocation-id="invocationId"
            :invocation-state="invocationState"
            :invocation-state-success="invocationStateSuccess"
            :running-count="runningCount" />
        <div v-else-if="!invocationAndJobTerminal">
            <b-alert variant="info" show>
                <LoadingSpan :message="`Waiting to complete invocation ${indexStr}`" />
            </b-alert>
            <span
                v-b-tooltip.hover
                class="fa fa-times cancel-workflow-scheduling"
                title="Cancel scheduling of workflow invocation"
                @click="onCancel"></span>
        </div>
        <template v-if="invocation.messages?.length">
            <InvocationMessage
                v-for="message in invocation.messages"
                :key="message.reason"
                class="steps-progress my-1"
                :invocation-message="message"
                :invocation="invocation">
            </InvocationMessage>
        </template>
        <InvocationStepsProgressBar
            v-else
            :invocation="invocation"
            :invocation-state="invocationState"
            :invocation-scheduling-terminal="invocationSchedulingTerminal" />
        <InvocationJobsProgressBar
            :job-states-summary="jobStatesSummary"
            :invocation-scheduling-terminal="invocationSchedulingTerminal"
            :invocation-and-job-terminal="invocationAndJobTerminal" />
    </div>
</template>
