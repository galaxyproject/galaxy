/* VueJS mixin with computed properties from a base jobStatesSummary property for summarizing job states */
export default {
    computed: {
        isNew() {
            return !this.jobStatesSummary || this.jobStatesSummary.new();
        },
        isErrored() {
            return this.jobStatesSummary && this.jobStatesSummary.errored();
        },
        isTerminal() {
            return this.jobStatesSummary && this.jobStatesSummary.terminal();
        },
        jobCount() {
            return !this.jobStatesSummary ? null : this.jobStatesSummary.jobCount();
        },
        jobsStr() {
            const jobCount = this.jobCount;
            return jobCount && jobCount > 1 ? `${jobCount} jobs` : `a job`;
        },
        runningCount() {
            return this.countStates(["running"]);
        },
        okCount() {
            return this.countStates(["ok"]);
        },
        errorCount() {
            return this.countStates(["error"]);
        },
        runningPercent() {
            return this.runningCount / (this.jobCount * 1.0);
        },
        okPercent() {
            return this.okCount / (this.jobCount * 1.0);
        },
        errorPercent() {
            return this.errorCount / (this.jobCount * 1.0);
        },
        otherPercent() {
            return 1.0 - this.okPercent - this.runningPercent - this.errorPercent;
        },
    },
    methods: {
        countStates(states) {
            let count = 0;
            if (this.jobStatesSummary && this.jobStatesSummary.hasDetails()) {
                for (const state of states) {
                    count += this.jobStatesSummary.states()[state] || 0;
                }
            }
            return count;
        },
    },
};
