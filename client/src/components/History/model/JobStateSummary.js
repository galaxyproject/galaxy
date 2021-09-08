/**
 * Read-only class takes raw data and applies some rules
 * to determine an amalgam state for a collection.
 *
 * Logic stolen from job-state-model.js and hdca-li.js
 */
import { STATES } from "./states";

const NON_TERMINAL_STATES = [STATES.NEW, STATES.WAITING, STATES.QUEUED, STATES.RUNNING];
const ERROR_STATES = [STATES.ERROR, STATES.DELETED];

export class JobStateSummary extends Map {
    constructor(dsc = {}) {
        const { job_state_summary = {}, populated_state = null } = dsc;
        super(Object.entries(job_state_summary));
        this.populated_state = populated_state;
    }

    hasJobs(key) {
        return this.has(key) ? this.get(key) > 0 : false;
    }

    // any of the passed states has jobs > 0
    anyHasJobs(...states) {
        return states.some((s) => this.hasJobs(s));
    }

    get state() {
        if (this.jobCount) {
            if (this.isErrored) {
                return STATES.ERROR;
            }
            if (this.isRunning) {
                return STATES.RUNNING;
            }
            if (this.isNew) {
                return STATES.LOADING;
            }
            if (this.isTerminal) {
                return STATES.OK;
            }
            return STATES.QUEUED;
        }
        return this.populated_state;
    }

    // Flags

    get isNew() {
        return !this.populated_state || this.populated_state == STATES.NEW;
    }

    get isErrored() {
        return this.populated_state == STATES.ERROR || this.anyHasJobs(...ERROR_STATES);
    }

    get isTerminal() {
        if (this.isNew) {
            return false;
        }
        return !this.anyHasJobs(...NON_TERMINAL_STATES);
    }

    get isRunning() {
        return this.hasJobs(STATES.RUNNING);
    }

    // Counts

    get jobCount() {
        return this.get("all_jobs");
    }

    get errorCount() {
        return this.get(STATES.ERROR);
    }

    get runningCount() {
        return this.get(STATES.RUNNING);
    }
}
