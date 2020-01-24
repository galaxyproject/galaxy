<template>
    <div>
        <span v-if="provideContext">
            <b>Workflow Invocation State</b>
            <span v-if="createdTime"> (invoked at {{ createdTime }})</span>
        </span>
        <div v-bind:class="{ 'context-wrapped': provideContext }">
            <div>
                Step Scheduling
                <span
                    v-if="stepCount && !invocationSchedulingTerminal"
                    v-b-tooltip.hover
                    title="Cancel scheduling of workflow invocation"
                    class="fa fa-times"
                    @click="cancelWorkflowScheduling"
                ></span>
                <div v-if="!stepCount">
                    <progress-bar note="Loading step state summary" :loading="true" :infoProgress="1" />
                </div>
                <div v-else-if="invocationState == 'cancelled'">
                    <progress-bar
                        note="Invocation scheduling cancelled - expected jobs and outputs may not be generated"
                        :errorProgress="1"
                    />
                </div>
                <div v-else-if="invocationState == 'failed'">
                    <progress-bar
                        note="Invocation scheduling failed - Galaxy administrator may have additional details in logs"
                        :errorProgress="1"
                    />
                </div>
                <div v-else>
                    <progress-bar
                        :note="stepStatesStr"
                        :okProgress="stepScheduledPercent"
                        :newProgress="stepOtherPercent"
                    />
                </div>
            </div>
            <div>
                Job Execution
                <div v-if="jobCount">
                    <progress-bar
                        :note="jobStatesStr"
                        :okProgress="okPercent"
                        :runningProgress="runningPercent"
                        :newProgress="otherPercent"
                        :errorProgress="errorPercent"
                        :okMessage="okMessage"
                        :runningMessage="runningMessage"
                        :errorMessage="errorMessage"
                    />
                </div>
                <div v-else>
                    <progress-bar note="Loading job summary" :loading="true" :infoProgress="1" />
                </div>
            </div>
            <span v-if="invocationSchedulingTerminal && jobStatesTerminal">
                <a v-bind:href="invocationLink">View Invocation Report</a>
                <a class="fa fa-print" v-bind:href="invocationPdfLink"></a>
            </span>
        </div>
    </div>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import { cancelWorkflowScheduling } from "./services";

import { getRootFromIndexLink } from "onload";
import JOB_STATES_MODEL from "mvc/history/job-states-model";
import mixin from "components/JobStates/mixin";
import ProgressBar from "components/ProgressBar";

import { mapGetters, mapActions } from "vuex";

const getUrl = path => getRootFromIndexLink() + path;

Vue.use(BootstrapVue);

export default {
    components: {
        ProgressBar
    },
    mixins: [mixin],
    props: {
        invocationId: {
            type: String,
            required: true
        },
        provideContext: {
            type: Boolean,
            default: true
        }
    },
    data() {
        return {
            stepStatesInterval: null,
            jobStatesInterval: null
        };
    },
    created: function() {
        this.pollStepStatesUntilTerminal();
        this.pollJobStatesUntilTerminal();
    },
    computed: {
        ...mapGetters(["getInvocationById", "getInvocationJobsSummaryById"]),
        invocationState: function() {
            const invocation = this.getInvocationById(this.invocationId);
            const state = invocation ? invocation.state : "new";
            return state;
        },
        createdTime: function() {
            const invocation = this.getInvocationById(this.invocationId);
            return invocation ? this.getInvocationById(this.invocationId).create_time : null;
        },
        stepCount: function() {
            const invocation = this.getInvocationById(this.invocationId);
            if (invocation) {
                return invocation.steps.length;
            } else {
                return null;
            }
        },
        stepStates: function() {
            const stepStates = {};
            const invocation = this.getInvocationById(this.invocationId);
            if (!invocation) {
                return {};
            }
            for (const step of invocation.steps) {
                if (!stepStates[step.state]) {
                    stepStates[step.state] = 1;
                } else {
                    stepStates[step.state] += 1;
                }
            }
            return stepStates;
        },
        invocationLink: function() {
            return getUrl(`workflows/invocations/report?id=${this.invocationId}`);
        },
        invocationPdfLink: function() {
            return getUrl(`api/invocations/${this.invocationId}/report.pdf`);
        },
        invocationSchedulingTerminal: function() {
            return (
                this.invocationState == "scheduled" ||
                this.invocationState == "cancelled" ||
                this.invocationState == "failed"
            );
        },
        jobStatesTerminal: function() {
            return this.jobStatesSummary && this.jobStatesSummary.terminal();
        },
        stepScheduledPercent: function() {
            let percent = 0.0;
            if (this.stepCount !== null) {
                percent = (this.stepStates["scheduled"] || 0) / this.stepCount;
            }
            return percent;
        },
        stepOtherPercent: function() {
            const percent = 1.0 - this.stepScheduledPercent;
            return percent;
        },
        stepStatesStr: function() {
            return `${this.stepStates["scheduled"] || 0} of ${this.stepCount} steps successfully scheduled`;
        },
        jobStatesStr: function() {
            let jobStr = `${this.jobStatesSummary.states()["ok"] || 0} of ${this.jobCount} jobs complete`;
            if (!this.invocationSchedulingTerminal) {
                jobStr += " (total number of jobs will change until all steps fully scheduled)";
            }
            return jobStr;
        },
        okMessage() {
            return `${this.okCount} jobs completed successfully`;
        },
        errorMessage() {
            return `${this.errorCount} jobs failed`;
        },
        runningMessage() {
            return `${this.runningCount} jobs currently running`;
        },
        jobStatesSummary() {
            const jobsSummary = this.getInvocationJobsSummaryById(this.invocationId);
            return !jobsSummary ? null : new JOB_STATES_MODEL.JobStatesSummary(jobsSummary);
        }
    },
    methods: {
        ...mapActions(["fetchInvocationForId", "fetchInvocationJobsSummaryForId"]),
        pollStepStatesUntilTerminal: function() {
            clearInterval(this.stepStatesInterval);
            if (!this.invocationSchedulingTerminal) {
                this.fetchInvocationForId(this.invocationId);
                this.stepStatesInterval = setInterval(this.pollStepStatesUntilTerminal, 3000);
            }
        },
        pollJobStatesUntilTerminal: function() {
            clearInterval(this.jobStatesInterval);
            if (!this.jobStatesTerminal) {
                this.fetchInvocationJobsSummaryForId(this.invocationId);
                this.jobStatesInterval = setInterval(this.pollJobStatesUntilTerminal, 3000);
            }
        },
        onError: function(e) {
            console.error(e);
        },
        cancelWorkflowScheduling: function() {
            cancelWorkflowScheduling(this.invocationId).catch(this.onError);
        }
    },
    beforeDestroy: function() {
        clearInterval(this.jobStatesInterval);
        clearInterval(this.stepStatesInterval);
    }
};
</script>
<style scoped>
.context-wrapped {
    border-left: 1px solid black;
    padding-left: 10px;
}
</style>
