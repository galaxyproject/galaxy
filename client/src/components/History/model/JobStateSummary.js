/**
 * Read-only class takes raw data and applies some rules
 * to determine an amalgam state for a collection.
 */
import { STATES } from "./states";

// logic largely stolen from the butchered, degenerate mess at:
// import nonsense from "mvc/history/job-states-model.js"

// Job-state-summary lists

const NON_TERMINAL_STATES = [STATES.NEW, STATES.QUEUED, STATES.RUNNING];

const ERROR_STATES = [
    STATES.ERROR,
    STATES.DELETED, // does this exist?
];

export class JobStateSummary extends Map {
    constructor(dsc = {}) {
        const { job_state_summary = {}, populated_state = null } = dsc;
        super(Object.entries(job_state_summary));
        this.populated_state = populated_state;
    }

    // state element has value > 0
    hasJobs(key) {
        return this.has(key) ? this.get(key) > 0 : false;
    }

    // any of the passed states has jobs > 0
    anyHasJobs(...states) {
        return states.some((s) => this.hasJobs(s));
    }

    // amalgam state, basically just for display purposes
    get state() {
        // FROM mvc/history/hdca-li.js
        //TODO: model currently has no state
        // var state;
        // var jobStatesSummary = this.model.jobStatesSummary;
        // if (jobStatesSummary) {
        //     if (jobStatesSummary.new()) {
        //         state = "loading";
        //     } else if (jobStatesSummary.errored()) {
        //         state = "error";
        //     } else if (jobStatesSummary.terminal()) {
        //         state = "ok";
        //     } else if (jobStatesSummary.running()) {
        //         state = "running";
        //     } else {
        //         state = "queued";
        //     }
        // } else if (this.model.get("job_source_id")) {
        //     // Initial rendering - polling will fill in more details in a bit.
        //     state = "loading";
        // } else {
        //     state = this.model.get("populated_state") ? STATES.OK : STATES.RUNNING;
        // }

        if (this.jobCount) {
            if (this.isErrored) return STATES.ERROR;
            if (this.isNew) return STATES.NEW;
            if (this.isRunning) return STATES.RUNNING;
            if (this.isTerminal) return STATES.OK;
            return STATES.QUEUED;
        }

        return null;
    }

    // Flags

    get isNew() {
        return !this.populated_state || this.populated_state == STATES.NEW;
    }

    get isErrored() {
        return this.anyHasJobs(...ERROR_STATES);
    }

    get isRunning() {
        return this.hasJobs(STATES.RUNNING);
    }

    get isTerminal() {
        if (this.isNew) return false;
        return !this.anyHasJobs(...NON_TERMINAL_STATES);
    }

    // Counts

    get jobCount() {
        return this.get("all_jobs");
    }

    get errorCount() {
        return this.get(STATES.ERROR);
    }

    get runningCount() {
        return this.get(STATES.ERRUNNINGROR);
    }
}
