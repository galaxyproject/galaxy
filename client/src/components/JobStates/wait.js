import { getAppRoot } from "onload/loadConfig";
import JOB_STATES_MODEL from "mvc/history/job-states-model";
import axios from "axios";

export function waitOnJob(jobId, onStateUpdate = null, interval = 1000) {
    // full=true to capture standard error on last iteration for building
    // error messages.
    const jobUrl = `${getAppRoot()}api/jobs/${jobId}?full=true`;
    const checkCondition = function (resolve, reject) {
        axios
            .get(jobUrl)
            .then((jobResponse) => {
                const state = jobResponse.data.state;
                if (onStateUpdate !== null) {
                    onStateUpdate(state);
                }
                if (JOB_STATES_MODEL.NON_TERMINAL_STATES.indexOf(state) !== -1) {
                    setTimeout(checkCondition, interval, resolve, reject);
                } else if (JOB_STATES_MODEL.ERROR_STATES.indexOf(state) !== -1) {
                    reject(jobResponse);
                } else {
                    resolve(jobResponse);
                }
            })
            .catch(reject);
    };

    return new Promise(checkCondition);
}
