<template>
    <b-tabs v-if="invocation">
        <b-tab title="Summary" active>
            <workflow-invocation-summary
                :invocation="invocation"
                :index="index"
                :invocation-and-job-terminal="invocationAndJobTerminal"
                :invocation-scheduling-terminal="invocationSchedulingTerminal"
                :job-states-summary="jobStatesSummary"
                @invocation-cancelled="cancelWorkflowScheduling" />
        </b-tab>
        <b-tab title="Details">
            <workflow-invocation-details
                :invocation="invocation"
                :invocation-and-job-terminal="invocationAndJobTerminal" />
        </b-tab>
        <b-tab title="Workflow Overview">
            <p>TODO: Insert readonly version of workflow editor here</p>
        </b-tab>
        <b-tab title="Export">
            <div v-if="invocationAndJobTerminal">
                <workflow-invocation-export-options :invocation-id="invocation.id" />
            </div>
            <div v-else>
                <p v-localize>Waiting for invocation to complete...</p>
            </div>
        </b-tab>
    </b-tabs>
    <div v-else>
        <p v-localize>Loading invocation...</p>
    </div>
</template>
<script>
import { cancelWorkflowScheduling } from "./services";
import WorkflowInvocationSummary from "./WorkflowInvocationSummary.vue";
import WorkflowInvocationDetails from "./WorkflowInvocationDetails.vue";
import WorkflowInvocationExportOptions from "./WorkflowInvocationExportOptions.vue";

import JOB_STATES_MODEL from "mvc/history/job-states-model";
import mixin from "components/JobStates/mixin";
import { mapGetters, mapActions } from "vuex";

export default {
    components: {
        WorkflowInvocationSummary,
        WorkflowInvocationDetails,
        WorkflowInvocationExportOptions,
    },
    mixins: [mixin],
    props: {
        invocationId: {
            type: String,
            required: true,
        },
        index: {
            type: Number,
            required: false,
            default: null,
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
        invocation: function () {
            return this.getInvocationById(this.invocationId);
        },
        invocationState: function () {
            return this.invocation?.state || "new";
        },
        invocationAndJobTerminal: function () {
            return !!(this.invocationSchedulingTerminal && this.jobStatesTerminal);
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
