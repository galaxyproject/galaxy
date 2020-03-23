<template>
    <span>
        <b-alert variant="error" show v-if="error">
            {{ error }}
        </b-alert>
        <b-alert v-if="loading" variant="info" show>
            <loading-span message="Loading workflow run data" />
        </b-alert>
        <workflow-run-success v-else-if="invocations != null" :invocations="invocations" :workflowName="workflowName" />
        <div v-else ref="run" class="ui-form-composite">
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
                    icon="fa-check"
                    :disabled="!runButtonEnabled"
                    :waiting="!runButtonEnabled"
                    :waitText="runButtonWaitText"
                    :percentage="runButtonPercentage"
                    @click="execute"
                >
                </wait-button>
            </div>
            <div class="ui-form-composite-form" ref="form"></div>
        </div>
    </span>
</template>

<script>
import axios from "axios";

import WaitButton from "components/WaitButton";
import LoadingSpan from "components/LoadingSpan";
import WorkflowRunSuccess from "./WorkflowRunSuccess";
import { getAppRoot } from "onload";
import ToolFormComposite from "mvc/tool/tool-form-composite";
import { errorMessageAsString } from "utils/simple-error";

export default {
    components: {
        LoadingSpan,
        WaitButton,
        WorkflowRunSuccess,
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
        };
    },
    created() {
        const url = `${getAppRoot()}api/workflows/${this.workflowId}/download?style=run`;
        axios
            .get(url)
            .then((response) => {
                const runData = response.data;
                this.hasUpgradeMessages = runData.has_upgrade_messages;
                this.hasStepVersionChanges = runData.step_version_changes && runData.step_version_changes.length > 0;
                this.workflowName = runData.name;
                this.loading = false;
                this.$nextTick(() => {
                    const el = this.$refs["form"];
                    const formProps = {
                        el,
                        setRunButtonStatus: this.setRunButtonStatus,
                        handleInvocations: this.handleInvocations,
                    };
                    this.runForm = new ToolFormComposite.View(Object.assign({}, runData, formProps));
                });
            })
            .catch((response) => {
                this.error = errorMessageAsString(response);
            });
    },
    methods: {
        execute() {
            this.runForm.execute();
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
