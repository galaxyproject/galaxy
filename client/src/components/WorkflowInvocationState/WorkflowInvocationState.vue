<template>
    <div class="mb-3 workflow-invocation-state-component">
        <div v-if="invocationAndJobTerminal">
            <span>
                <a class="invocation-report-link" :href="invocationLink"
                    ><b>View Report {{ indexStr }}</b></a
                >
                <a
                    v-b-tooltip
                    class="fa fa-print ml-1 invocation-pdf-link"
                    :href="invocationPdfLink"
                    title="Download PDF" />
            </span>
        </div>
        <div v-else>
            <span class="fa fa-spinner fa-spin" />
            <span>Invocation {{ indexStr }}...</span>
            <span
                v-if="!invocationSchedulingTerminal"
                v-b-tooltip.hover
                class="fa fa-times cancel-workflow-scheduling"
                title="Cancel scheduling of workflow invocation"
                @click="cancelWorkflowScheduling"></span>
        </div>
        <progress-bar v-if="!stepCount" note="Loading step state summary..." :loading="true" class="steps-progress" />
        <progress-bar
            v-else-if="invocationState == 'cancelled'"
            note="Invocation scheduling cancelled - expected jobs and outputs may not be generated."
            :error-count="1"
            class="steps-progress" />
        <progress-bar
            v-else-if="invocationState == 'failed'"
            note="Invocation scheduling failed - Galaxy administrator may have additional details in logs."
            :error-count="1"
            class="steps-progress" />
        <progress-bar
            v-else
            :note="stepStatesStr"
            :total="stepCount"
            :ok-count="stepStates.scheduled"
            :loading="!invocationSchedulingTerminal"
            class="steps-progress" />
        <progress-bar
            :note="jobStatesStr"
            :total="jobCount"
            :ok-count="okCount"
            :running-count="runningCount"
            :new-count="newCount"
            :error-count="errorCount"
            :loading="!invocationAndJobTerminal"
            class="jobs-progress" />
        <span v-if="invocationAndJobTerminal">
            <a class="bco-json" :href="bcoJSON"><b>Download BioCompute Object</b></a>
        </span>
        <workflow-invocation-details
            v-if="invocation"
            :invocation="invocation"
            :invocation-and-job-terminal="invocationAndJobTerminal" />
    </div>
</template>
<script>
import { cancelWorkflowScheduling } from "./services";
import { getRootFromIndexLink } from "onload";
import WorkflowInvocationDetails from "./WorkflowInvocationDetails";

import JOB_STATES_MODEL from "mvc/history/job-states-model";
import mixin from "components/JobStates/mixin";
import ProgressBar from "components/ProgressBar";

import { mapGetters, mapActions } from "vuex";

const getUrl = (path) => getRootFromIndexLink() + path;

export default {
    components: {
        ProgressBar,
        WorkflowInvocationDetails,
    },
    mixins: [mixin],
    props: {
        invocationId: {
            type: String,
            required: true,
        },
        index: {
            type: Number,
            optional: true,
        },
    },
    data() {
        return {
            stepStatesInterval: null,
            jobStatesInterval: null,
        };
    },
    computed: {
        ...mapGetters(["getInvocationById", "getInvocationJobsSummaryById"]),
        indexStr() {
            if (this.index == null) {
                return "";
            } else {
                return `${this.index + 1}`;
            }
        },
        invocation: function () {
            return this.getInvocationById(this.invocationId);
        },
        invocationState: function () {
            return this.invocation?.state || "new";
        },
        createdTime: function () {
            return this.invocation?.create_time || null;
        },
        stepCount: function () {
            return this.invocation?.steps.length;
        },
        stepStates: function () {
            const stepStates = {};
            if (!this.invocation) {
                return {};
            }
            for (const step of this.invocation.steps) {
                if (!stepStates[step.state]) {
                    stepStates[step.state] = 1;
                } else {
                    stepStates[step.state] += 1;
                }
            }
            return stepStates;
        },
        invocationAndJobTerminal: function () {
            return !!(this.invocationSchedulingTerminal && this.jobStatesTerminal);
        },
        invocationLink: function () {
            return getUrl(`workflows/invocations/report?id=${this.invocationId}`);
        },
        bcoJSON: function () {
            return getUrl(`api/invocations/${this.invocationId}/biocompute/download`);
        },
        invocationPdfLink: function () {
            return getUrl(`api/invocations/${this.invocationId}/report.pdf`);
        },
        invocationSchedulingTerminal: function () {
            return (
                this.invocationState == "scheduled" ||
                this.invocationState == "cancelled" ||
                this.invocationState == "failed"
            );
        },
        jobStatesTerminal: function () {
            if (this.invocationSchedulingTerminal && this.JobStatesSummary?.jobCount === 0) {
                // no jobs for this invocation (think subworkflow or just inputs)
                return true;
            }
            return this.jobStatesSummary && this.jobStatesSummary.terminal();
        },
        stepStatesStr: function () {
            return `${this.stepStates.scheduled || 0} of ${this.stepCount} steps successfully scheduled.`;
        },
        jobStatesStr: function () {
            let jobStr = `${this.jobStatesSummary?.numTerminal() || 0} of ${this.jobCount} jobs complete`;
            if (!this.invocationSchedulingTerminal) {
                jobStr += " (total number of jobs will change until all steps fully scheduled)";
            }
            return `${jobStr}.`;
        },
        jobStatesSummary() {
            const jobsSummary = this.getInvocationJobsSummaryById(this.invocationId);
            return !jobsSummary ? null : new JOB_STATES_MODEL.JobStatesSummary(jobsSummary);
        },
    },
    created: function () {
        this.pollStepStatesUntilTerminal();
        this.pollJobStatesUntilTerminal();
    },
    beforeDestroy: function () {
        clearTimeout(this.jobStatesInterval);
        clearTimeout(this.stepStatesInterval);
    },
    methods: {
        ...mapActions(["fetchInvocationForId", "fetchInvocationJobsSummaryForId"]),
        pollStepStatesUntilTerminal: function () {
            if (!this.invocation || !this.invocationSchedulingTerminal) {
                this.fetchInvocationForId(this.invocationId).then((response) => {
                    this.stepStatesInterval = setTimeout(this.pollStepStatesUntilTerminal, 3000);
                });
            }
        },
        pollJobStatesUntilTerminal: function () {
            if (!this.jobStatesTerminal) {
                this.fetchInvocationJobsSummaryForId(this.invocationId).then((response) => {
                    this.jobStatesInterval = setTimeout(this.pollJobStatesUntilTerminal, 3000);
                });
            }
        },
        onError: function (e) {
            console.error(e);
        },
        onCancel() {
            this.$emit("invocation-cancelled");
        },
        cancelWorkflowScheduling: function () {
            cancelWorkflowScheduling(this.invocationId).then(this.onCancel).catch(this.onError);
        },
    },
};
</script>
