import { type InvocationJobsSummary } from "@/api/invocations";

export const NON_TERMINAL_STATES = ["new", "queued", "running", "waiting"];
export const ERROR_STATES = ["error", "deleted"];
export const TERMINAL_STATES = ["ok", "skipped"].concat(ERROR_STATES);
export const POPULATED_STATE_FAILED = "failed";

function countStates(jobSummary: InvocationJobsSummary | null, queryStates: string[]): number {
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

export function errorCount(jobSummary: InvocationJobsSummary): number {
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
