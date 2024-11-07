<script setup lang="ts">
import { onBeforeUnmount, onMounted, toRef } from "vue";

import { useInvocationState } from "@/components/WorkflowInvocationState/usesInvocationState";

import HelpText from "@/components/Help/HelpText.vue";
import InvocationJobsProgressBar from "@/components/WorkflowInvocationState/InvocationJobsProgressBar.vue";
import InvocationStepsProgressBar from "@/components/WorkflowInvocationState/InvocationStepsProgressBar.vue";

interface Props {
    invocationId: string;
    invocationState: string;
    detailsShowing: boolean;
}

const props = defineProps<Props>();

const {
    invocation,
    invocationState,
    invocationSchedulingTerminal,
    invocationAndJobTerminal,
    jobStatesSummary,
    monitorState,
    clearStateMonitor,
} = useInvocationState(toRef(props, "invocationId"), "step_states");

onMounted(monitorState);
onBeforeUnmount(clearStateMonitor);
</script>

<template>
    <span>
        <HelpText
            v-if="!invocation || detailsShowing"
            :uri="`galaxy.invocations.states.${props.invocationState}`"
            :text="props.invocationState" />
        <template v-else>
            <InvocationStepsProgressBar
                :invocation="invocation"
                :invocation-state="invocationState"
                :invocation-scheduling-terminal="invocationSchedulingTerminal" />
            <InvocationJobsProgressBar
                v-if="jobStatesSummary"
                :job-states-summary="jobStatesSummary"
                :invocation-scheduling-terminal="invocationSchedulingTerminal"
                :invocation-and-job-terminal="invocationAndJobTerminal" />
        </template>
    </span>
</template>
