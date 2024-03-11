<script setup lang="ts">
import { computed } from "vue";

import { InvocationJobsSummary, InvocationStep, WorkflowInvocationElementView } from "@/api/invocations";
import { getRootFromIndexLink } from "@/onload";

import {
    errorCount as jobStatesSummaryErrorCount,
    jobCount as jobStatesSummaryJobCount,
    numTerminal,
    okCount as jobStatesSummaryOkCount,
    runningCount as jobStatesSummaryRunningCount,
} from "./util";

import LoadingSpan from "@/components/LoadingSpan.vue";
import ProgressBar from "@/components/ProgressBar.vue";

import InvocationMessage from "./InvocationMessage.vue";
import InvocationSummaryActionButtons from "./InvocationSummaryActionButtons.vue";

function getUrl(path: string): string {
    return getRootFromIndexLink() + path;
}

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

const stepCount = computed<number>(() => {
    return props.invocation?.steps.length || 0;
});

type StepStateType = { [state: string]: number };

const stepStates = computed<StepStateType>(() => {
    const stepStates: StepStateType = {};
    if (!props.invocation) {
        return {};
    }
    const steps: InvocationStep[] = props.invocation?.steps || [];
    for (const step of steps) {
        if (!step) {
            continue;
        }
        // the API defined state here allowing null and undefined is odd...
        const stepState: string = step.state || "unknown";
        if (!stepStates[stepState]) {
            stepStates[stepState] = 1;
        } else {
            stepStates[stepState] += 1;
        }
    }
    return stepStates;
});

const stepStatesStr = computed<string>(() => {
    return `${stepStates.value?.scheduled || 0} of ${stepCount.value} steps successfully scheduled.`;
});

const okCount = computed<number>(() => {
    return jobStatesSummaryOkCount(props.jobStatesSummary);
});

const runningCount = computed<number>(() => {
    return jobStatesSummaryRunningCount(props.jobStatesSummary);
});

const jobCount = computed<number>(() => {
    return jobStatesSummaryJobCount(props.jobStatesSummary);
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
        <ProgressBar v-if="!stepCount" note="Loading step state summary..." :loading="true" class="steps-progress" />
        <template v-if="invocation.messages?.length">
            <InvocationMessage
                v-for="message in invocation.messages"
                :key="message.reason"
                class="steps-progress my-1"
                :invocation-message="message"
                :invocation="invocation">
            </InvocationMessage>
        </template>
        <ProgressBar
            v-else-if="invocationState == 'cancelled'"
            note="Invocation scheduling cancelled - expected jobs and outputs may not be generated."
            :error-count="1"
            class="steps-progress" />
        <ProgressBar
            v-else-if="invocationState == 'failed'"
            note="Invocation scheduling failed - Galaxy administrator may have additional details in logs."
            :error-count="1"
            class="steps-progress" />
        <ProgressBar
            v-else
            :note="stepStatesStr"
            :total="stepCount"
            :ok-count="stepStates.scheduled"
            :loading="!invocationSchedulingTerminal"
            class="steps-progress" />
        <ProgressBar
            :note="jobStatesStr"
            :total="jobCount"
            :ok-count="okCount"
            :running-count="runningCount"
            :new-count="newCount"
            :error-count="errorCount"
            :loading="!invocationAndJobTerminal"
            class="jobs-progress" />
    </div>
</template>
