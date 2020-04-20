<template>
    <span>
        <b-alert variant="error" show v-if="error">
            {{ error }}
        </b-alert>
        <b-alert v-if="loading" variant="info" show>
            <loading-span message="Loading workflow run data" />
        </b-alert>
        <workflow-run-success v-else-if="invocations != null" :invocations="invocations" :workflowName="workflowName" />
        <div v-else class="ui-form-composite">
            <div class="ui-form-composite-messages mb-4">
                <b-alert v-if="hasUpgradeMessages" variant="warning" show>
                    Some tools in this workflow may have changed since it was last saved or some errors were found. The
                    workflow may still run, but any new options will have default values. Please review the messages
                    below to make a decision about whether the changes will affect your analysis.
                </b-alert>
                <b-alert v-if="hasStepVersionChanges" variant="warning" show>
                    Some tools are being executed with different versions compared to those available when this workflow
                    was last saved because the other versions are not or no longer available on this Galaxy instance. To
                    upgrade your workflow and dismiss this message simply edit the workflow and re-save it.
                </b-alert>
            </div>
            <!-- h4 as a class here looks odd but it was in the Backbone -->
            <div class="ui-form-composite-header h4">
                <b>Workflow: {{ workflowName }}</b>
                <wait-button
                    title="Run Workflow"
                    id="run-workflow"
                    variant="primary"
                    :disabled="!runButtonEnabled"
                    :waiting="!runButtonEnabled"
                    :waitText="runButtonWaitText"
                    :percentage="runButtonPercentage"
                    @click="execute"
                >
                </wait-button>
            </div>
            <workflow-run-form
                ref="run-form"
                :runData="runData"
                :setRunButtonStatus="setRunButtonStatus"
                @submissionSuccess="handleInvocations"
            />
        </div>
    </span>
</template>

<script>
import axios from "axios";

import WaitButton from "components/WaitButton";
import LoadingSpan from "components/LoadingSpan";
import WorkflowRunSuccess from "./WorkflowRunSuccess";
import WorkflowRunForm from "./WorkflowRunForm";
import { getAppRoot } from "onload";
import { errorMessageAsString } from "utils/simple-error";

export default {
    components: {
        LoadingSpan,
        WaitButton,
        WorkflowRunSuccess,
        WorkflowRunForm,
    },
    props: {
        workflowId: { type: String },
    },
    data() {
        return {
            error: false,
            loading: true,
            hasUpgradeMessages: false,
            hasStepVersionChanges: false,
            workflowName: "",
            runForm: null,
            runButtonEnabled: true,
            runButtonWaitText: "",
            runButtonPercentage: -1,
            invocations: null,
            runData: null,
        };
    },
    created() {
        const url = `${getAppRoot()}api/workflows/${this.workflowId}/download?style=run`;
        axios
            .get(url)
            .then((response) => {
                const runData = response.data;
                this.runData = runData;
                this.hasUpgradeMessages = runData.has_upgrade_messages;
                this.hasStepVersionChanges = runData.step_version_changes && runData.step_version_changes.length > 0;
                this.workflowName = runData.name;
                this.loading = false;
            })
            .catch((response) => {
                this.error = errorMessageAsString(response);
            });
    },
    methods: {
        execute() {
            this.$refs["run-form"].execute();
        },
        setRunButtonStatus(enabled, waitText, percentage) {
            this.runButtonEnabled = enabled;
            this.runButtonWaitText = waitText;
            this.runButtonPercentage = percentage;
        },
        handleInvocations(invocations) {
            this.invocations = invocations;
        },
    },
};
</script>
