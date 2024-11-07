import { computed, type Ref } from "vue";

import {
    type InvocationJobsSummary,
    type LegacyWorkflowInvocationElementView,
    type WorkflowInvocationElementView,
    type WorkflowInvocationStepStatesView,
} from "@/api/invocations";
import { useInvocationStore } from "@/stores/invocationStore";

import { isTerminal, jobCount } from "./util";

type OptionalInterval = ReturnType<typeof setInterval> | null;

export function useInvocationState(invocationId: Ref<string>, view: "element" | "step_states" | "legacy" = "element") {
    const invocationStore = useInvocationStore();

    const invocation = computed(() => {
        if (view === "step_states") {
            return invocationStore.getInvocationWithStepStatesById(
                invocationId.value
            ) as WorkflowInvocationStepStatesView;
        } else if (view === "legacy") {
            return invocationStore.getInvocationWithJobStepIdsById(
                invocationId.value
            ) as LegacyWorkflowInvocationElementView;
        } else {
            return invocationStore.getInvocationById(invocationId.value) as WorkflowInvocationElementView;
        }
    });

    let stepStatesInterval: OptionalInterval = null;
    let jobStatesInterval: OptionalInterval = null;

    const invocationState = computed(() => {
        return invocation.value?.state || "new";
    });

    const invocationSchedulingTerminal = computed(() => {
        const state = invocationState.value;
        return state == "scheduled" || state == "cancelled" || state == "failed";
    });

    const invocationAndJobTerminal = computed(() => {
        return !!(invocationSchedulingTerminal.value && jobStatesTerminal.value);
    });

    const jobStatesTerminal = computed(() => {
        if (invocationSchedulingTerminal.value && jobCount(jobStatesSummary.value) === 0) {
            // no jobs for this invocation (think subworkflow or just inputs)
            return true;
        }
        return jobStatesSummary.value && isTerminal(jobStatesSummary.value);
    });

    const jobStatesSummary = computed<InvocationJobsSummary | null>(() => {
        const jobsSummary: InvocationJobsSummary | null = invocationStore.getInvocationJobsSummaryById(
            invocationId.value
        );
        return !jobsSummary ? null : jobsSummary;
    });

    async function pollStepStatesUntilTerminal() {
        if (!invocation.value || !invocationSchedulingTerminal.value) {
            if (view === "step_states") {
                await invocationStore.fetchInvocationWithStepStatesForId({ id: invocationId.value });
            } else if (view === "legacy") {
                await invocationStore.fetchInvocationWithJobStepIdsForId({ id: invocationId.value });
            } else {
                await invocationStore.fetchInvocationForId({ id: invocationId.value });
            }
            stepStatesInterval = setTimeout(pollStepStatesUntilTerminal, 3000);
        }
    }

    async function pollJobStatesUntilTerminal() {
        if (!jobStatesTerminal.value) {
            await invocationStore.fetchInvocationJobsSummaryForId({ id: invocationId.value });
            jobStatesInterval = setTimeout(pollJobStatesUntilTerminal, 3000);
        }
    }

    async function monitorState() {
        pollStepStatesUntilTerminal();
        pollJobStatesUntilTerminal();
    }

    async function clearStateMonitor() {
        if (jobStatesInterval) {
            clearTimeout(jobStatesInterval);
        }
        if (stepStatesInterval) {
            clearTimeout(stepStatesInterval);
        }
    }

    return {
        invocation,
        invocationState,
        invocationSchedulingTerminal,
        invocationAndJobTerminal,
        jobStatesSummary,
        monitorState,
        clearStateMonitor,
    };
}
