import JOB_STATES_MODEL from "mvc/history/job-states-model";
import { snakeCase } from "snake-case";

export function stateIsTerminal(result) {
    return !JOB_STATES_MODEL.NON_TERMINAL_STATES.includes(result.state);
}

// Adapt bootstrap parameters to Galaxy API. Galaxy consumes snake case parameters
// and generally uses limit instead of perPage/per_page as a name for this concept.
export function cleanPaginationParameters(requestParams) {
    const cleanParams = {};
    Object.entries(requestParams).map(([key, val]) => {
        if (key === "perPage") {
            key = "limit";
        }
        if (val) {
            cleanParams[snakeCase(key)] = val;
        }
    });
    if (cleanParams.current_page && cleanParams.limit) {
        cleanParams.offset = (cleanParams.current_page - 1) * cleanParams.limit;
        delete cleanParams.current_page;
    }
    return cleanParams;
}
