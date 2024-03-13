<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount } from "vue";

import { InvocationJobsSummary, WorkflowInvocationElementView } from "@/api/invocations";

import LoadingSpan from "@/components/LoadingSpan.vue";

import { useInvocationStore } from "@/stores/invocationStore";

import { cancelWorkflowScheduling } from "./services";
import { isTerminal, jobCount } from "./util";

import WorkflowInvocationDetails from "./WorkflowInvocationDetails.vue";
import WorkflowInvocationExportOptions from "./WorkflowInvocationExportOptions.vue";
import WorkflowInvocationSummary from "./WorkflowInvocationSummary.vue";

interface Props {
    invocationId: string;
    index?: Number;
}

const props = defineProps<Props>();

const invocationStore = useInvocationStore();

type OptionalInterval = ReturnType<typeof setInterval> | null;

let stepStatesInterval: OptionalInterval = null;
let jobStatesInterval: OptionalInterval = null;

const invocation = computed(() => {
    return invocationStore.getInvocationById(props.invocationId);
});

const invocationState = computed(() => {
    return invocation.value?.state || "new";
});

const invocationAndJobTerminal = computed(() => {
    return !!(invocationSchedulingTerminal.value && jobStatesTerminal.value);
});

const invocationSchedulingTerminal = computed(() => {
    const state = invocationState.value;
    return state == "scheduled" || state == "cancelled" || state == "failed";
});

const jobStatesTerminal = computed(() => {
    if (invocationSchedulingTerminal.value && jobCount(jobStatesSummary.value) === 0) {
        // no jobs for this invocation (think subworkflow or just inputs)
        return true;
    }
    return jobStatesSummary.value && isTerminal(jobStatesSummary.value);
});

const jobStatesSummary = computed<InvocationJobsSummary | null>(() => {
    const jobsSummary: InvocationJobsSummary | null = invocationStore.getInvocationJobsSummaryById(props.invocationId);
    return !jobsSummary ? null : jobsSummary;
});

async function pollStepStatesUntilTerminal() {
    if (!invocation.value || !invocationSchedulingTerminal.value) {
        await invocationStore.fetchInvocationForId({ id: props.invocationId });
        stepStatesInterval = setTimeout(pollStepStatesUntilTerminal, 3000);
    }
}

async function pollJobStatesUntilTerminal() {
    if (!jobStatesTerminal.value) {
        await invocationStore.fetchInvocationJobsSummaryForId({ id: props.invocationId });
        jobStatesInterval = setTimeout(pollJobStatesUntilTerminal, 3000);
    }
}

onMounted(() => {
    pollStepStatesUntilTerminal();
    pollJobStatesUntilTerminal();
});

onBeforeUnmount(() => {
    if (jobStatesInterval) {
        clearTimeout(jobStatesInterval);
    }
    if (stepStatesInterval) {
        clearTimeout(stepStatesInterval);
    }
});

function onError(e: unknown) {
    console.error(e);
}

const emit = defineEmits<{
    (e: "invocation-cancelled"): void;
}>();

function onCancel() {
    emit("invocation-cancelled");
}

function handleCancelWorkflowScheduling() {
    cancelWorkflowScheduling(props.invocationId).then(onCancel).catch(onError);
}
</script>

<template>
    <b-tabs v-if="invocation">
        <b-tab title="Summary" active>
            <WorkflowInvocationSummary
                class="invocation-summary"
                :invocation="invocation"
                :index="index"
                :invocation-and-job-terminal="invocationAndJobTerminal"
                :invocation-scheduling-terminal="invocationSchedulingTerminal"
                :job-states-summary="jobStatesSummary"
                @invocation-cancelled="handleCancelWorkflowScheduling" />
        </b-tab>
        <b-tab title="Details">
            <WorkflowInvocationDetails :invocation="invocation" />
        </b-tab>
        <!-- <b-tab title="Workflow Overview">
            <p>TODO: Insert readonly version of workflow editor here</p>
        </b-tab> -->
        <b-tab title="Export">
            <div v-if="invocationAndJobTerminal">
                <WorkflowInvocationExportOptions :invocation-id="invocation.id" />
            </div>
            <b-alert v-else variant="info" show>
                <LoadingSpan message="Waiting to complete invocation" />
            </b-alert>
        </b-tab>
    </b-tabs>
    <b-alert v-else variant="info" show>
        <LoadingSpan message="Loading invocation" />
    </b-alert>
</template>
