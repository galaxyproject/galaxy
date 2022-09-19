<template>
    <span>
        <b-alert v-if="error" variant="danger" show>
            <h5>Workflow cannot be executed. Please resolve the following issue:</h5>
            {{ error }}
        </b-alert>
        <span v-else>
            <b-alert v-if="loading" variant="info" show>
                <loading-span message="Loading workflow run data" />
            </b-alert>
            <workflow-run-success v-else-if="!!invocations" :invocations="invocations" :workflow-name="workflowName" />
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
                    <b-alert v-if="submissionError" variant="danger" show>
                        Workflow submission failed: {{ submissionError }}
                    </b-alert>
                </div>
                <workflow-run-form-simple
                    v-if="simpleForm"
                    :model="model"
                    :target-history="simpleFormTargetHistory"
                    :use-job-cache="simpleFormUseJobCache"
                    @submissionSuccess="handleInvocations"
                    @submissionError="handleSubmissionError"
                    @showAdvanced="showAdvanced" />
                <workflow-run-form
                    v-else
                    :model="model"
                    @submissionSuccess="handleInvocations"
                    @submissionError="handleSubmissionError" />
            </div>
        </span>
    </span>
</template>

<script>
import { getRunData } from "./services";
import LoadingSpan from "components/LoadingSpan";
import WorkflowRunSuccess from "./WorkflowRunSuccess";
import WorkflowRunForm from "./WorkflowRunForm";
import WorkflowRunFormSimple from "./WorkflowRunFormSimple";
import { WorkflowRunModel } from "./model";
import { errorMessageAsString } from "utils/simple-error";

export default {
    components: {
        LoadingSpan,
        WorkflowRunSuccess,
        WorkflowRunForm,
        WorkflowRunFormSimple,
    },
    props: {
        workflowId: {
            type: String,
            required: true,
        },
        preferSimpleForm: {
            type: Boolean,
            default: false,
        },
        simpleFormTargetHistory: {
            type: String,
            default: "current",
        },
        simpleFormUseJobCache: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            runData: null,
            error: null,
            loading: true,
            invocations: null,
            submissionError: null,
        };
    },
    created() {
        getRunData(this.workflowId)
            .then((runData) => {
                this.runData = runData;
                this.loading = false;
            })
            .catch((response) => {
                this.error = errorMessageAsString(response);
            });
    },
    computed: {
        model() {
            return new WorkflowRunModel(this.runData);
        },
        simpleForm() {
            if (this.preferSimpleForm) {
                // These only work with PJA - the API doesn't evaluate them at
                // all outside that context currently. The main workflow form renders
                // these dynamically and takes care of all the validation and setup details
                // on the frontend. If these are implemented on the backend at some
                // point this restriction can be lifted.
                if (this.hasReplacementParametersInToolForm) {
                    console.debug("cannot render simple workflow form - has ${} values in tool steps");
                    return false;
                }
                // If there are required parameters in a tool form (a disconnected runtime
                // input), we have to render the tool form steps and cannot use the
                // simplified tool form.
                if (this.model.hasOpenToolSteps) {
                    console.debug(
                        "cannot render simple workflow form - one or more tools have disconnected runtime inputs"
                    );
                    return false;
                }
                // Just render the whole form for resource request parameters (kind of
                // niche - I'm not sure anyone is using these currently anyway).
                if (this.model.hasWorkflowResourceParameters) {
                    console.debug(`Cannot render simple workflow form - workflow resource parameters are configured`);
                    return false;
                }
            }
            return this.simpleForm;
        },
        hasUpgradeMessages() {
            return this.model.hasUpgradeMessages;
        },
        hasStepVersionChanges() {
            return this.model.hasStepVersionChanges;
        },
        workflowName() {
            return this.model.workflowName;
        },
    },
    methods: {
        handleInvocations(invocations) {
            this.invocations = invocations;
        },
        handleSubmissionError(error) {
            this.submissionError = errorMessageAsString(error);
        },
        showAdvanced() {
            this.simpleForm = false;
        },
    },
};
</script>
