<script setup lang="ts">
import { BAlert, BButton } from "bootstrap-vue";
import { computed } from "vue";

import { InvocationJobsSummary, InvocationStep, WorkflowInvocationElementView } from "@/api/invocations";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { getRootFromIndexLink } from "@/onload";
import { withPrefix } from "@/utils/redirect";

import {
    errorCount as jobStatesSummaryErrorCount,
    jobCount as jobStatesSummaryJobCount,
    numTerminal,
    okCount as jobStatesSummaryOkCount,
    runningCount as jobStatesSummaryRunningCount,
} from "./util";

import ExternalLink from "../ExternalLink.vue";
import HelpText from "../Help/HelpText.vue";
import InvocationGraph from "../Workflow/Invocation/Graph/InvocationGraph.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ProgressBar from "@/components/ProgressBar.vue";
import InvocationMessage from "@/components/WorkflowInvocationState/InvocationMessage.vue";

function getUrl(path: string): string {
    return getRootFromIndexLink() + path;
}

interface Props {
    invocation?: WorkflowInvocationElementView;
    invocationAndJobTerminal: boolean;
    invocationSchedulingTerminal: boolean;
    jobStatesSummary: InvocationJobsSummary;
    index?: number;
    isSubworkflow?: boolean;
}

const props = defineProps<Props>();

const reportTooltip = "View report for this workflow invocation";
const generatePdfTooltip = "Generate PDF report for this workflow invocation";

const { workflow } = useWorkflowInstance(props.invocation?.workflow_id ?? "");

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

const disabledReportTooltip = computed(() => {
    const state = invocationState.value;
    const runCount = runningCount.value;
    if (state != "scheduled") {
        return `This workflow is not currently scheduled. The current state is ${state}. Once the workflow is fully scheduled and jobs have complete this option will become available.`;
    } else if (runCount != 0) {
        return `The workflow invocation still contains ${runCount} running job(s). Once these jobs have completed this option will become available.`;
    } else {
        return "Steps for this workflow are still running. A report will be available once complete.";
    }
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

const invocationLink = computed<string | null>(() => {
    const id = invocationId.value;
    if (id) {
        return getUrl(`workflows/invocations/report?id=${id}`);
    } else {
        return null;
    }
});

const invocationPdfLink = computed<string | null>(() => {
    const id = invocationId.value;
    if (id) {
        return getUrl(`api/invocations/${id}/report.pdf`);
    } else {
        return null;
    }
});

const hasMessages = computed<boolean>(() => {
    return props.invocation?.messages.length ? true : false;
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
        <div v-if="!invocationAndJobTerminal">
            <BAlert variant="info" show>
                <LoadingSpan :message="`Waiting to complete invocation ${indexStr}`" />
            </BAlert>
            <BButton
                v-b-tooltip.noninteractive.hover
                class="cancel-workflow-scheduling"
                title="Cancel scheduling of workflow invocation"
                size="sm"
                @click="onCancel">
                <span class="fa fa-times mr-1" /> Cancel
            </BButton>
        </div>
        <div class="d-flex align-items-center">
            <div v-if="invocationAndJobTerminal" class="mr-1" :class="{ 'd-flex': !hasMessages }">
                <BButton
                    v-b-tooltip.hover
                    :title="invocationStateSuccess ? reportTooltip : disabledReportTooltip"
                    :disabled="!invocationStateSuccess"
                    size="sm"
                    class="invocation-report-link text-nowrap w-100"
                    :href="invocationLink">
                    View Report
                </BButton>
                <BButton
                    v-b-tooltip.hover
                    :title="invocationStateSuccess ? generatePdfTooltip : disabledReportTooltip"
                    :disabled="!invocationStateSuccess"
                    size="sm"
                    class="invocation-pdf-link text-nowrap w-100"
                    :class="{ 'mt-1': hasMessages }"
                    :href="invocationPdfLink"
                    target="_blank">
                    Generate PDF
                </BButton>
            </div>
            <div class="w-100">
                <ProgressBar
                    v-if="!stepCount"
                    note="Loading step state summary..."
                    :loading="true"
                    class="steps-progress" />
                <template v-if="invocation && hasMessages">
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
        </div>
        <!-- An invocation has been loaded, display the graph -->
        <div v-if="invocation">
            <div v-if="workflow && !isSubworkflow">
                <InvocationGraph
                    :invocation="invocation"
                    :workflow="workflow"
                    :is-terminal="invocationAndJobTerminal"
                    :is-scheduled="invocationSchedulingTerminal" />
            </div>
            <BAlert v-else-if="isSubworkflow" variant="secondary" show>
                This subworkflow is
                <HelpText :uri="`galaxy.invocations.states.${invocation.state}`" :text="invocation.state" />.
                <ExternalLink :href="withPrefix(`/workflows/invocations/${invocation.id}`)"> Click here </ExternalLink>
                to view this subworkflow in graph view.
            </BAlert>
        </div>
    </div>
</template>
