<script setup lang="ts">
import { computed } from "vue";

import { InvocationStep, WorkflowInvocationElementView } from "@/api/invocations";

import ProgressBar from "@/components/ProgressBar.vue";

interface Props {
    invocation?: WorkflowInvocationElementView;
    invocationState: string;
    invocationSchedulingTerminal: boolean;
}

const props = defineProps<Props>();

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
        const stepState: string = step.state;
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
</script>

<template>
    <span>
        <ProgressBar v-if="!stepCount" note="Loading step state summary..." :loading="true" class="steps-progress" />
        <ProgressBar
            v-if="invocationState == 'cancelled'"
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
    </span>
</template>
