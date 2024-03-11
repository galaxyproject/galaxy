<script setup lang="ts">
import { BAlert, BButton } from "bootstrap-vue";
import { computed } from "vue";

import { type InvocationJobsSummary, type WorkflowInvocationElementView } from "@/api/invocations";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { getRootFromIndexLink } from "@/onload";
import { withPrefix } from "@/utils/redirect";

import { runningCount as jobStatesSummaryRunningCount } from "./util";

import ExternalLink from "../ExternalLink.vue";
import HelpText from "../Help/HelpText.vue";
import InvocationGraph from "../Workflow/Invocation/Graph/InvocationGraph.vue";
import InvocationJobsProgressBar from "./InvocationJobsProgressBar.vue";
import InvocationStepsProgressBar from "./InvocationStepsProgressBar.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import InvocationMessage from "@/components/WorkflowInvocationState/InvocationMessage.vue";

function getUrl(path: string): string {
    return getRootFromIndexLink() + path;
}

interface Props {
    invocation: WorkflowInvocationElementView;
    invocationAndJobTerminal: boolean;
    invocationSchedulingTerminal: boolean;
    isFullPage?: boolean;
    jobStatesSummary: InvocationJobsSummary;
    index?: number;
    isSubworkflow?: boolean;
}

const props = defineProps<Props>();

const generatePdfTooltip = "Generate PDF report for this workflow invocation";

const { workflow, loading, error } = useWorkflowInstance(props.invocation.workflow_id);

const invocationId = computed<string | undefined>(() => props.invocation.id);

const indexStr = computed(() => {
    if (props.index == undefined) {
        return "";
    } else {
        return `${props.index + 1}`;
    }
});

const invocationState = computed(() => {
    return props.invocation.state || "new";
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

const invocationPdfLink = computed<string | null>(() => {
    const id = invocationId.value;
    if (id) {
        return getUrl(`api/invocations/${id}/report.pdf`);
    } else {
        return null;
    }
});

const uniqueMessages = computed(() => {
    const messages = props.invocation.messages || [];
    const uniqueMessagesSet = new Set(messages.map((message) => JSON.stringify(message)));
    return Array.from(uniqueMessagesSet).map((message) => JSON.parse(message)) as typeof messages;
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
        <BAlert v-if="isSubworkflow" variant="secondary" show>
            This subworkflow is
            <HelpText :uri="`galaxy.invocations.states.${invocation.state}`" :text="invocation.state" />.
            <ExternalLink :href="withPrefix(`/workflows/invocations/${invocation.id}`)"> Click here </ExternalLink>
            to view this subworkflow in graph view.
        </BAlert>
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
            <div v-if="invocationAndJobTerminal" class="mr-1" :class="{ 'd-flex': !uniqueMessages.length }">
                <BButton
                    v-b-tooltip.hover
                    :title="invocationStateSuccess ? generatePdfTooltip : disabledReportTooltip"
                    :disabled="!invocationStateSuccess"
                    size="sm"
                    class="invocation-pdf-link text-nowrap w-100"
                    :class="{ 'mt-1': uniqueMessages.length }"
                    :href="invocationPdfLink"
                    target="_blank">
                    Generate PDF
                </BButton>
            </div>
            <div class="w-100">
                <template v-if="uniqueMessages.length">
                    <InvocationMessage
                        v-for="message in uniqueMessages"
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
        </div>
        <!-- Once the workflow for the invocation has been loaded, display the graph -->
        <BAlert v-if="loading" variant="info" show>
            <LoadingSpan message="Loading workflow..." />
        </BAlert>
        <BAlert v-else-if="error" variant="danger" show>
            {{ error }}
        </BAlert>
        <div v-else-if="workflow && !isSubworkflow">
            <InvocationGraph
                class="mt-1"
                data-description="workflow invocation graph"
                :invocation="invocation"
                :workflow="workflow"
                :is-terminal="invocationAndJobTerminal"
                :is-scheduled="invocationSchedulingTerminal"
                :is-full-page="isFullPage"
                :show-minimap="isFullPage" />
        </div>
        <BAlert v-else-if="!workflow" variant="info" show> No workflow found for this invocation. </BAlert>
    </div>
</template>
