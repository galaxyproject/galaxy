<script setup lang="ts">
import { onBeforeUnmount, onMounted, toRef } from "vue";

import { WorkflowInvocationElementView } from "@/api/invocations";

import { cancelWorkflowScheduling } from "./services";
import { useInvocationState } from "./usesInvocationState";

import WorkflowInvocationDetails from "./WorkflowInvocationDetails.vue";
import WorkflowInvocationExportOptions from "./WorkflowInvocationExportOptions.vue";
import WorkflowInvocationSummary from "./WorkflowInvocationSummary.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    invocationId: string;
    index?: Number;
}

const props = defineProps<Props>();

const {
    invocation,
    invocationSchedulingTerminal,
    invocationAndJobTerminal,
    jobStatesSummary,
    monitorState,
    clearStateMonitor,
} = useInvocationState(toRef(props, "invocationId"));

onMounted(monitorState);
onBeforeUnmount(clearStateMonitor);

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
