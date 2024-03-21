<template>
    <b-tabs v-if="invocation">
        <b-tab title="Summary" active>
            <WorkflowInvocationSummary
                class="invocation-summary"
                :invocation="invocation"
                :index="index"
                :invocation-and-job-terminal="invocationAndJobTerminal"
                :invocation-scheduling-terminal="invocationSchedulingTerminal"
                :job-states-summary="jobStatesSummary"
                @invocation-cancelled="cancelWorkflowScheduling" />
        </b-tab>
        <b-tab title="Details">
            <WorkflowInvocationDetails :invocation="invocation" />
        </b-tab>
        <!-- <b-tab title="Workflow Overview">
            <p>TODO: Insert readonly version of workflow editor here</p>
        </b-tab> -->
        <b-tab title="Export">
            <div v-if="invocationAndJobTerminal">
                <WorkflowInvocationExportOptions :invocation-id="invocation.id" />
            </div>
            <b-alert v-else variant="info" show>
                <LoadingSpan message="Waiting to complete invocation" />
            </b-alert>
        </b-tab>
    </b-tabs>
    <b-alert v-else variant="info" show>
        <LoadingSpan message="Loading invocation" />
    </b-alert>
</template>
<script>
import mixin from "components/JobStates/mixin";
import LoadingSpan from "components/LoadingSpan";
import JOB_STATES_MODEL from "utils/job-states-model";

import { useInvocationStore } from "@/stores/invocationStore";

import { cancelWorkflowScheduling } from "./services";

import WorkflowInvocationDetails from "./WorkflowInvocationDetails.vue";
import WorkflowInvocationExportOptions from "./WorkflowInvocationExportOptions.vue";
import WorkflowInvocationSummary from "./WorkflowInvocationSummary.vue";

export default {
    components: {
        LoadingSpan,
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
    setup() {
        const invocationStore = useInvocationStore();
        return {
            invocationStore,
        };
    },
    data() {
        return {
            stepStatesInterval: null,
            jobStatesInterval: null,
        };
    },
    computed: {
        invocation: function () {
            return this.invocationStore.getInvocationById(this.invocationId);
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
            const jobsSummary = this.invocationStore.getInvocationJobsSummaryById(this.invocationId);
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
        pollStepStatesUntilTerminal: async function () {
            if (!this.invocation || !this.invocationSchedulingTerminal) {
                await this.invocationStore.fetchInvocationForId({ id: this.invocationId });
                this.stepStatesInterval = setTimeout(this.pollStepStatesUntilTerminal, 3000);
            }
        },
        pollJobStatesUntilTerminal: async function () {
            if (!this.jobStatesTerminal) {
                await this.invocationStore.fetchInvocationJobsSummaryForId({ id: this.invocationId });
                this.jobStatesInterval = setTimeout(this.pollJobStatesUntilTerminal, 3000);
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
