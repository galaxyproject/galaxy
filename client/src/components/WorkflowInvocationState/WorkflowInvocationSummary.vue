<template>
    <div class="mb-3 workflow-invocation-state-component">
        <div v-if="invocationAndJobTerminal">
            <span>
                <a class="invocation-report-link" :href="invocationLink">
                    <b>View Report {{ indexStr }}</b>
                </a>
                <a
                    v-b-tooltip
                    class="fa fa-print ml-1 invocation-pdf-link"
                    :href="invocationPdfLink"
                    title="Download PDF" />
            </span>
        </div>
        <div v-else-if="!invocationSchedulingTerminal">
            <b-alert variant="info" show>
                <LoadingSpan :message="`Waiting to complete invocation ${indexStr}`" />
            </b-alert>
            <span
                v-b-tooltip.hover
                class="fa fa-times cancel-workflow-scheduling"
                title="Cancel scheduling of workflow invocation"
                @click="onCancel"></span>
        </div>
        <progress-bar v-if="!stepCount" note="Loading step state summary..." :loading="true" class="steps-progress" />
        <template v-if="invocation.messages?.length">
            <invocation-message
                v-for="message in invocation.messages"
                :key="message.reason"
                class="steps-progress my-1"
                :invocation-message="message"
                :invocation="invocation">
            </invocation-message>
        </template>
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
    </div>
</template>
<script>
import { getRootFromIndexLink } from "onload";
import mixin from "components/JobStates/mixin";
import ProgressBar from "components/ProgressBar";
import LoadingSpan from "components/LoadingSpan";
import InvocationMessage from "@/components/WorkflowInvocationState/InvocationMessage.vue";

import { mapGetters } from "vuex";

const getUrl = (path) => getRootFromIndexLink() + path;

export default {
    components: {
        InvocationMessage,
        ProgressBar,
        LoadingSpan,
    },
    mixins: [mixin],
    props: {
        invocation: {
            type: Object,
            required: true,
        },
        invocationAndJobTerminal: {
            type: Boolean,
            required: true,
        },
        invocationSchedulingTerminal: {
            type: Boolean,
            required: true,
        },
        jobStatesSummary: {
            type: Object,
            required: false,
            default: null,
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
        invocationId() {
            return this.invocation?.id;
        },
        indexStr() {
            if (this.index == null) {
                return "";
            } else {
                return `${this.index + 1}`;
            }
        },
        invocationState: function () {
            return this.invocation?.state || "new";
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
        invocationLink: function () {
            return getUrl(`workflows/invocations/report?id=${this.invocationId}`);
        },
        invocationPdfLink: function () {
            return getUrl(`api/invocations/${this.invocationId}/report.pdf`);
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
    },
    methods: {
        onCancel() {
            this.$emit("invocation-cancelled");
        },
    },
};
</script>
