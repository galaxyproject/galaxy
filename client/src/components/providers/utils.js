import JOB_STATES_MODEL from "mvc/history/job-states-model";

export function stateIsTerminal(result) {
    return !JOB_STATES_MODEL.NON_TERMINAL_STATES.includes(result.state);
}
