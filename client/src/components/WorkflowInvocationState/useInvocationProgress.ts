import { computed, type MaybeRefOrGetter, toValue } from "vue";

import type { InvocationStep, WorkflowInvocationElementView } from "@/api/invocations";
import { useInvocationStore } from "@/stores/invocationStore";

import {
    errorCount as jobStatesSummaryErrorCount,
    isTerminal,
    jobCount as jobStatesSummaryJobCount,
    numTerminal,
    okCount as jobStatesSummaryOkCount,
    runningCount as jobStatesSummaryRunningCount,
} from "./util";

/**
 * An invocation's scheduling and job progress, read from what the invocation store already holds.
 * It fetches and polls nothing itself; `WorkflowInvocationState` keeps that data fresh.
 * @param invocationId The invocation's id, for its jobs summary
 * @param invocation The invocation's element view, once loaded
 */
export function useInvocationProgress(
    invocationId: MaybeRefOrGetter<string>,
    invocation: MaybeRefOrGetter<WorkflowInvocationElementView | null>,
) {
    const invocationStore = useInvocationStore();

    const invocationState = computed(() => toValue(invocation)?.state || "new");
    const invocationAndJobTerminal = computed(() => invocationSchedulingTerminal.value && jobStatesTerminal.value);
    const invocationSchedulingTerminal = computed(() => {
        return (
            invocationState.value == "scheduled" ||
            invocationState.value == "cancelled" ||
            invocationState.value == "failed" ||
            invocationState.value == "completed"
        );
    });
    const jobStatesTerminal = computed(() => {
        // If the job states summary is null, we haven't fetched it yet
        // If the `populated_state` for the summary is `new`, we haven't finished scheduling all jobs
        if (jobStatesSummary.value === null || jobStatesSummary.value.populated_state === "new") {
            return false;
        }

        if (invocationSchedulingTerminal.value && jobCount.value === 0) {
            // no jobs for this invocation (think it has just subworkflows/inputs)
            return true;
        }
        return isTerminal(jobStatesSummary.value);
    });
    const jobStatesSummary = computed(() => invocationStore.getInvocationJobsSummaryById(toValue(invocationId)));

    type StepStateType = { [state: string]: number };

    const stepStates = computed<StepStateType>(() => {
        const stepStates: StepStateType = {};
        const steps: InvocationStep[] = toValue(invocation)?.steps || [];
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

    const stepCount = computed<number>(() => {
        return toValue(invocation)?.steps.length || 0;
    });

    const stepStatesStr = computed<string>(() => {
        return `${stepStates.value?.scheduled || 0} of ${stepCount.value} steps successfully scheduled.`;
    });

    const stateCounts = computed<{
        okCount: number;
        errorCount: number;
        runningCount: number;
        newCount: number;
    } | null>(() => {
        if (jobStatesSummary.value === null) {
            return null;
        }
        const okCount = jobStatesSummaryOkCount(jobStatesSummary.value);
        const errorCount = jobStatesSummaryErrorCount(jobStatesSummary.value);
        const runningCount = jobStatesSummaryRunningCount(jobStatesSummary.value);
        const newCount = jobCount.value - okCount - runningCount - errorCount;
        return { okCount, errorCount, runningCount, newCount };
    });

    const jobCount = computed<number>(() => {
        return jobStatesSummaryJobCount(jobStatesSummary.value);
    });

    const jobStatesStr = computed(() => {
        if (jobStatesSummary.value === null) {
            return "No jobs summary available yet.";
        }

        let jobStr = `${numTerminal(jobStatesSummary.value) || 0} of ${jobCount.value} jobs complete`;
        if (!invocationSchedulingTerminal.value) {
            jobStr += " (total number of jobs will change until all steps fully scheduled)";
        }
        return `${jobStr}.`;
    });

    return {
        invocationState,
        invocationSchedulingTerminal,
        invocationAndJobTerminal,
        jobStatesSummary,
        jobStatesTerminal,
        jobCount,
        stateCounts,
        jobStatesStr,
        stepStates,
        stepCount,
        stepStatesStr,
    };
}
