<template>
    <span>
        <b-alert v-if="invocationId" variant="success" show>
            You are rerunning invocation {{ invocationId }}. Please be aware that parameters which are unlabelled or not
            explicitly defined have been reset to their default values.
        </b-alert>
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
import { getRunData, getInvocationData } from "./services";
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
        invocationId: {
            type: String,
            default: "",
        },
    },
    data() {
        return {
            error: null,
            loading: true,
            hasUpgradeMessages: false,
            hasStepVersionChanges: false,
            workflowName: "",
            invocations: null,
            simpleForm: null,
            submissionError: null,
            model: null,
        };
    },
    created() {
        var invDataPromise;
        var runDataPromise = getRunData(this.workflowId);
        if (this.invocationId) {
            invDataPromise = getInvocationData(this.invocationId);
        } else {
            invDataPromise = Promise.resolve();
        }

        Promise.all([runDataPromise, invDataPromise])
            .then((data) => {
                const runData = data[0];
                const invocationData = data[1];
                if (this.invocationId) {
                    Object.keys(runData.steps).forEach(function (step) {
                        Object.keys(invocationData.inputs).every(function (inv_input) {
                            if (invocationData.inputs[inv_input].workflow_step_id == runData.steps[step].step_id) {
                                var value = {
                                    id: invocationData.inputs[inv_input].id,
                                    hid: invocationData.inputs[inv_input].hid,
                                    name: invocationData.inputs[inv_input].name,
                                    src: invocationData.inputs[inv_input].src,
                                    keep: "false",
                                };
                                runData.steps[step].inputs[0].value = {
                                    values: [value],
                                }; // multiple values are not possible for invocations
                                if (invocationData.inputs[inv_input].src == "hda") {
                                    Object.keys(runData.steps[step].inputs[0].options.hda).every(function (hda) {
                                        if (
                                            runData.steps[step].inputs[0].options.hda[hda].id ==
                                            invocationData.inputs[inv_input].id
                                        ) {
                                            runData.steps[step].inputs[0].options.hda.splice(hda, 1);
                                            runData.steps[step].inputs[0].options.hda.splice(0, 0, value);
                                            return false;
                                        }
                                        return true;
                                    });
                                    return false;
                                }
                                if (invocationData.inputs[inv_input].src == "hdca") {
                                    Object.keys(runData.steps[step].inputs[0].options.hdca).every(function (hdca) {
                                        if (
                                            runData.steps[step].inputs[0].options.hdca[hdca].id ==
                                            invocationData.inputs[inv_input].id
                                        ) {
                                            runData.steps[step].inputs[0].options.hdca.splice(hdca, 1);
                                            runData.steps[step].inputs[0].options.hdca.splice(0, 0, value);
                                            return false;
                                        }
                                        return true;
                                    });
                                }
                                return false;
                            }
                            Object.keys(invocationData.input_step_parameters).every(function (inv_param) {
                                if (
                                    invocationData.input_step_parameters[inv_param].workflow_step_id ==
                                    runData.steps[step].step_id
                                ) {
                                    runData.steps[step].inputs[0].value =
                                        invocationData.input_step_parameters[inv_param].parameter_value;
                                    return false;
                                }
                                return true;
                            });
                            return true;
                        });
                    });
                }

                this.loading = false;
                const model = new WorkflowRunModel(runData);
                let simpleForm = this.preferSimpleForm;
                if (simpleForm) {
                    // These only work with PJA - the API doesn't evaluate them at
                    // all outside that context currently. The main workflow form renders
                    // these dynamically and takes care of all the validation and setup details
                    // on the frontend. If these are implemented on the backend at some
                    // point this restriction can be lifted.
                    if (model.hasReplacementParametersInToolForm) {
                        console.log("cannot render simple workflow form - has ${} values in tool steps");
                        simpleForm = false;
                    }
                    // If there are required parameters in a tool form (a disconnected runtime
                    // input), we have to render the tool form steps and cannot use the
                    // simplified tool form.
                    if (model.hasOpenToolSteps) {
                        console.log(
                            "cannot render simple workflow form - one or more tools have disconnected runtime inputs"
                        );
                        simpleForm = false;
                    }
                    // Just render the whole form for resource request parameters (kind of
                    // niche - I'm not sure anyone is using these currently anyway).
                    if (model.hasWorkflowResourceParameters) {
                        console.log(`Cannot render simple workflow form - workflow resource parameters are configured`);
                        simpleForm = false;
                    }
                }
                this.simpleForm = simpleForm;
                this.model = model;
                this.hasUpgradeMessages = model.hasUpgradeMessages;
                this.hasStepVersionChanges = model.hasStepVersionChanges;
                this.workflowName = this.model.name;
            })
            .catch((response) => {
                this.error = errorMessageAsString(response);
            });
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
