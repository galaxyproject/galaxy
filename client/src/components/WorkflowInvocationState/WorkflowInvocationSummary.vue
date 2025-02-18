<template>
    <div class="mb-3 workflow-invocation-state-component">
        <div v-if="invocationAndJobTerminal">
            <span>
                <b-button
                    v-b-tooltip.hover
                    :title="invocationStateSuccess ? reportTooltip : disabledReportTooltip"
                    :disabled="!invocationStateSuccess"
                    size="sm"
                    class="invocation-report-link"
                    :href="invocationLink">
                    View Report
                </b-button>
                <b-button
                    v-if="isConfigLoaded && config.enable_beta_markdown_export"
                    v-b-tooltip.hover
                    :title="invocationStateSuccess ? generatePdfTooltip : disabledReportTooltip"
                    :disabled="!invocationStateSuccess"
                    size="sm"
                    class="invocation-pdf-link"
                    :href="invocationPdfLink"
                    target="_blank">
                    Generate PDF
                </b-button>
            </span>
        </div>
        <div v-else-if="!invocationAndJobTerminal">
            <b-alert variant="info" show>
                <LoadingSpan :message="`Waiting to complete invocation ${indexStr}`" />
            </b-alert>
            <span
                v-b-tooltip.hover
                class="fa fa-times cancel-workflow-scheduling"
                title="Cancel scheduling of workflow invocation"
                @click="onCancel"></span>
        </div>
        <ProgressBar v-if="!stepCount" note="Loading step state summary..." :loading="true" class="steps-progress" />
        <template v-if="invocation.messages?.length">
            <InvocationMessage
                v-for="message in invocation.messages"
                :key="message.reason"
                class="steps-progress my-1"
                :invocation-message="message"
                :invocation="invocation">
            </InvocationMessage>
        </template>
        <ProgressBar
            v-else-if="invocationState == 'cancelled'"
            note="Invocation scheduling cancelled - expected jobs and outputs may not be generated."
            :error-count="1"
            class="steps-progress" />
        <ProgressBar
            v-else-if="invocationState == 'failed'"
            note="Invocation scheduling failed - Galaxy administrator may have additional details in logs."
            :error-count="1"
            class="steps-progress" />
        <ProgressBar
            v-else
            :note="stepStatesStr"
            :total="stepCount"
            :ok-count="stepStates.scheduled"
            :loading="!invocationSchedulingTerminal"
            class="steps-progress" />
        <ProgressBar
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
import mixin from "components/JobStates/mixin";
import LoadingSpan from "components/LoadingSpan";
import ProgressBar from "components/ProgressBar";
import { getRootFromIndexLink } from "onload";

import { useConfig } from "@/composables/config";

import InvocationMessage from "@/components/WorkflowInvocationState/InvocationMessage.vue";

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
    setup() {
        const { config, isConfigLoaded } = useConfig(true);
        return { config, isConfigLoaded };
    },
    data() {
        return {
            stepStatesInterval: null,
            jobStatesInterval: null,
            reportTooltip: "View report for this workflow invocation",
            generatePdfTooltip: "Generate PDF report for this workflow invocation",
        };
    },
    computed: {
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
        invocationStateSuccess: function () {
            return this.invocationState == "scheduled" && this.runningCount === 0 && this.invocationAndJobTerminal;
        },
        disabledReportTooltip: function () {
            const state = this.invocationState;
            const runCount = this.runningCount;
            if (this.invocationState != "scheduled") {
                return (
                    "This workflow is not currently scheduled. The current state is ",
                    state,
                    ". Once the workflow is fully scheduled and jobs have complete this option will become available."
                );
            } else if (runCount != 0) {
                return (
                    "The workflow invocation still contains ",
                    runCount,
                    " running job(s). Once these jobs have completed this option will become available. "
                );
            } else {
                return "Steps for this workflow are still running. A report will be available once complete.";
            }
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
