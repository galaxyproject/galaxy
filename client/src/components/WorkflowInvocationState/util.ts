import type { InvocationJobsSummary, StepJobSummary } from "@/api/invocations";
import { ERROR_STATES, NON_TERMINAL_STATES, TERMINAL_STATES } from "@/api/jobs";

import type { ReasonToLevel } from "./types";

export { ERROR_STATES, NON_TERMINAL_STATES, TERMINAL_STATES } from "@/api/jobs";

export const POPULATED_STATE_FAILED = "failed";

export const INVOCATION_MSG_LEVEL: ReasonToLevel = {
    history_deleted: "cancel",
    user_request: "cancel",
    cancelled_on_review: "cancel",
    dataset_failed: "error",
    collection_failed: "error",
    job_failed: "error",
    output_not_found: "error",
    expression_evaluation_failed: "error",
    when_not_boolean: "error",
    unexpected_failure: "error",
    workflow_output_not_found: "warning",
    workflow_parameter_invalid: "error",
};

function countStates(jobSummary: InvocationJobsSummary | StepJobSummary | null, queryStates: string[]): number {
    let count = 0;
    const states = jobSummary?.states;
    if (states) {
        for (const state of queryStates) {
            count += jobSummary.states[state] || 0;
        }
    }
    return count;
}

export function jobCount(jobSummary: InvocationJobsSummary | null) {
    const states = jobSummary?.states;
    let count = 0;
    if (states) {
        for (const index in states) {
            const stateCount = states[index];
            if (stateCount) {
                count += stateCount;
            }
        }
    }
    return count;
}

export function okCount(jobSummary: InvocationJobsSummary): number {
    return countStates(jobSummary, ["ok", "skipped"]);
}

export function runningCount(jobSummary: InvocationJobsSummary): number {
    return countStates(jobSummary, ["running"]);
}

export function numTerminal(jobSummary: InvocationJobsSummary): number {
    return countStates(jobSummary, TERMINAL_STATES);
}

export function errorCount(jobSummary: InvocationJobsSummary | StepJobSummary): number {
    return countStates(jobSummary, ERROR_STATES);
}

function isNew(jobSummary: InvocationJobsSummary) {
    return jobSummary.populated_state && jobSummary.populated_state == "new";
}

function anyWithStates(jobSummary: InvocationJobsSummary, queryStates: string[]) {
    const states = jobSummary.states;
    for (const index in queryStates) {
        const state: string = queryStates[index] as string;
        if ((states[state] || 0) > 0) {
            return true;
        }
    }
    return false;
}

export function isTerminal(jobSummary: InvocationJobsSummary) {
    if (isNew(jobSummary)) {
        return false;
    } else {
        const anyNonTerminal = anyWithStates(jobSummary, NON_TERMINAL_STATES);
        return !anyNonTerminal;
    }
}
