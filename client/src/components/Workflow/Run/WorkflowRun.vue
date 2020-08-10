<template>
    <span>
        <b-alert variant="danger" show v-if="error">
            {{ error }}
        </b-alert>
        <span v-else>
            <b-alert v-if="loading" variant="info" show>
                <loading-span message="Loading workflow run data" />
            </b-alert>
            <workflow-run-success
                v-else-if="invocations != null"
                :invocations="invocations"
                :workflow-name="workflowName"
            />
            <div v-else class="ui-form-composite">
                <div class="ui-form-composite-messages mb-4">
                    <b-alert v-if="hasUpgradeMessages" variant="warning" show>
                        Some tools in this workflow may have changed since it was last saved or some errors were found.
                        The workflow may still run, but any new options will have default values. Please review the
                        messages below to make a decision about whether the changes will affect your analysis.
                    </b-alert>
                    <b-alert v-if="hasStepVersionChanges" variant="warning" show>
                        Some tools are being executed with different versions compared to those available when this
                        workflow was last saved because the other versions are not or no longer available on this Galaxy
                        instance. To upgrade your workflow and dismiss this message simply edit the workflow and re-save
                        it.
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
                        :wait-text="runButtonWaitText"
                        :percentage="runButtonPercentage"
                        @click="execute"
                    >
                    </wait-button>
                </div>
                <workflow-run-form
                    ref="runform"
                    :model="model"
                    :set-run-button-status="setRunButtonStatus"
                    @submissionSuccess="handleInvocations"
                />
            </div>
        </span>
    </span>
</template>

<script>
import { getRunData } from "./services.js";
import WaitButton from "components/WaitButton";
import LoadingSpan from "components/LoadingSpan";
import WorkflowRunSuccess from "./WorkflowRunSuccess";
import WorkflowRunForm from "./WorkflowRunForm";
import { WorkflowRunModel } from "./model.js";
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
            error: null,
            loading: true,
            hasUpgradeMessages: false,
            hasStepVersionChanges: false,
            workflowName: "",
            runForm: null,
            runButtonEnabled: true,
            runButtonWaitText: "",
            runButtonPercentage: -1,
            invocations: null,
            model: null,
        };
    },
    created() {
        getRunData(this.workflowId)
            .then((runData) => {
                const model = new WorkflowRunModel(runData);
                this.model = model;
                this.hasUpgradeMessages = model.hasUpgradeMessages;
                this.hasStepVersionChanges = model.hasStepVersionChanges;
                this.workflowName = this.model.name;
                this.loading = false;
            })
            .catch((response) => {
                this.error = errorMessageAsString(response);
            });
    },
    methods: {
        execute() {
            this.$refs.runform.execute();
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
