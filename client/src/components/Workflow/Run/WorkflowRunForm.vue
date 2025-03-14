<template>
    <div v-if="currentUser && currentHistoryId" class="workflow-expanded-form">
        <BAlert v-if="!canRunOnHistory" variant="warning" show>
            <span v-localize>
                The workflow cannot run because the current history is immutable. Please select a different history or
                send the results to a new one.
            </span>
        </BAlert>
        <div class="h4 clearfix mb-3">
            <b>Workflow: {{ model.name }}</b> <i>(version: {{ model.runData.version + 1 }})</i>
            <div class="float-right d-flex flex-gapx-1">
                <b-button
                    v-if="!disableSimpleForm"
                    v-b-tooltip.hover.noninteractive
                    variant="link"
                    class="text-decoration-none"
                    title="Use simplified run form instead"
                    @click="$emit('showSimple')">
                    <span class="fas fa-arrow-left" /> Simple Form
                </b-button>
                <ButtonSpinner
                    id="run-workflow"
                    title="Run Workflow"
                    :disabled="!canRunOnHistory"
                    :wait="showExecuting"
                    @onClick="onExecute" />
            </div>
        </div>
        <FormCard v-if="wpInputsAvailable" title="Workflow Parameters">
            <template v-slot:body>
                <FormDisplay :inputs="wpInputs" @onChange="onWpInputs" />
            </template>
        </FormCard>
        <FormCard title="History Options">
            <template v-slot:body>
                <FormDisplay :inputs="historyInputs" @onChange="onHistoryInputs" />
            </template>
        </FormCard>
        <FormCard v-if="reuseAllowed(currentUser)" title="Job re-use Options">
            <template v-slot:body>
                <FormElement
                    v-model="useCachedJobs"
                    title="Attempt to re-use jobs with identical parameters?"
                    help="This may skip executing jobs that you have already run."
                    type="boolean" />
            </template>
        </FormCard>
        <FormCard v-if="resourceInputsAvailable" title="Workflow Resource Options">
            <template v-slot:body>
                <FormDisplay :inputs="resourceInputs" @onChange="onResourceInputs" />
            </template>
        </FormCard>
        <div v-for="step in model.steps" :key="step.index">
            <WorkflowRunDefaultStep
                v-if="step.step_type == 'tool' || step.step_type == 'subworkflow'"
                :model="step"
                :replace-params="getReplaceParams(step.inputs)"
                :validation-scroll-to="getValidationScrollTo(step.index)"
                :history-id="currentHistoryId"
                @onChange="onToolStepInputs"
                @onValidation="onValidation" />
            <WorkflowRunInputStep
                v-else
                :model="step"
                :validation-scroll-to="getValidationScrollTo(step.index)"
                @onChange="onDefaultStepInputs"
                @onValidation="onValidation" />
        </div>
    </div>
</template>

<script>
import { BAlert } from "bootstrap-vue";
import ButtonSpinner from "components/Common/ButtonSpinner";
import FormCard from "components/Form/FormCard";
import FormDisplay from "components/Form/FormDisplay";
import FormElement from "components/Form/FormElement";
import { allowCachedJobs } from "components/Tool/utilities";
import { mapState } from "pinia";

import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import { getReplacements } from "./model";
import { invokeWorkflow } from "./services";
import WorkflowRunDefaultStep from "./WorkflowRunDefaultStep";
import WorkflowRunInputStep from "./WorkflowRunInputStep";

export default {
    components: {
        BAlert,
        ButtonSpinner,
        FormDisplay,
        FormCard,
        FormElement,
        WorkflowRunDefaultStep,
        WorkflowRunInputStep,
    },
    props: {
        model: {
            type: Object,
            required: true,
        },
        canMutateCurrentHistory: {
            type: Boolean,
            required: true,
        },
        disableSimpleForm: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            showExecuting: false,
            stepData: {},
            stepValidations: {},
            stepScrollTo: {},
            wpData: {},
            inputs: {},
            historyData: {},
            useCachedJobs: false,
            historyInputs: [
                {
                    type: "conditional",
                    name: "new_history",
                    test_param: {
                        name: "check",
                        label: "Send results to a new history",
                        type: "boolean",
                        value: "false",
                        help: "",
                    },
                    cases: [
                        {
                            value: "true",
                            inputs: [
                                {
                                    name: "name",
                                    label: "History name",
                                    type: "text",
                                    value: this.model.name,
                                },
                            ],
                        },
                        {
                            value: "false",
                            inputs: [],
                        },
                    ],
                },
            ],
        };
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
        ...mapState(useHistoryStore, ["currentHistoryId"]),
        resourceInputsAvailable() {
            return this.resourceInputs.length > 0;
        },
        resourceInputs() {
            return this.toArray(this.model.workflowResourceParameters);
        },
        wpInputsAvailable() {
            return this.wpInputs.length > 0;
        },
        wpInputs() {
            return this.toArray(this.model.wpInputs);
        },
        shouldRunOnNewHistory() {
            return Boolean(this.historyData["new_history|name"]);
        },
        canRunOnHistory() {
            return this.shouldRunOnNewHistory || this.canMutateCurrentHistory;
        },
    },
    methods: {
        reuseAllowed(user) {
            return allowCachedJobs(user.preferences);
        },
        getReplaceParams(inputs) {
            return getReplacements(inputs, this.stepData, this.wpData);
        },
        getValidationScrollTo(stepId) {
            if (this.stepScrollTo.stepId == stepId) {
                return this.stepScrollTo.stepError;
            }
            return [];
        },
        onDefaultStepInputs(stepId, data) {
            this.inputs[stepId] = data.input;
        },
        onToolStepInputs(stepId, data) {
            this.stepData[stepId] = data;
        },
        onHistoryInputs(data) {
            this.historyData = data;
        },
        onResourceInputs(data) {
            this.resourceData = data;
        },
        onWpInputs(data) {
            this.wpData = data;
        },
        onValidation(stepId, validation) {
            this.stepValidations[stepId] = validation;
        },
        onExecute() {
            for (const [stepId, stepValidation] of Object.entries(this.stepValidations)) {
                if (stepValidation) {
                    this.stepScrollTo = {
                        stepId: stepId,
                        stepError: stepValidation.slice(),
                    };
                    return;
                }
            }

            const parameters = {};
            Object.entries(this.stepData).forEach(([stepId, stepData]) => {
                const stepDataFiltered = {};
                Object.entries(stepData).forEach(([inputName, inputValue]) => {
                    if (!this.model.isConnected(stepId, inputName)) {
                        stepDataFiltered[inputName] = inputValue;
                    }
                });
                parameters[stepId] = stepDataFiltered;
            });

            const jobDef = {
                new_history_name: this.historyData["new_history|name"] ? this.historyData["new_history|name"] : null,
                history_id: !this.historyData["new_history|name"] ? this.model.historyId : null,
                resource_params: this.resourceData,
                replacement_params: this.wpData,
                use_cached_job: this.useCachedJobs,
                inputs: this.inputs,
                parameters: parameters,
                // Tool form will submit flat maps for each parameter
                // (e.g. "repeat_0|cond|param": "foo" instead of nested
                // data structures).
                parameters_normalized: true,
                // Tool form always wants a list of invocations back
                // so that inputs can be batched.
                batch: true,
                // the user is already warned if tool versions are wrong,
                // they can still choose to invoke the workflow anyway.
                require_exact_tool_versions: false,
                version: this.model.runData.version,
            };

            console.debug("WorkflowRunForm::onExecute()", "Ready for submission.", jobDef);
            this.showExecuting = true;
            invokeWorkflow(this.model.workflowId, jobDef)
                .then((invocations) => {
                    console.debug("WorkflowRunForm::onExecute()", "Submission successful.", invocations);
                    this.showExecuting = false;
                    this.$emit("submissionSuccess", invocations);
                })
                .catch((e) => {
                    console.debug("WorkflowRunForm::onExecute()", "Submission failed.", e);
                    this.showExecuting = false;
                    const errorData = e && e.response && e.response.data && e.response.data.err_data;
                    if (errorData) {
                        try {
                            const errorEntries = Object.entries(errorData);
                            this.stepScrollTo = {
                                stepId: errorEntries[0][0],
                                stepError: Object.entries(errorEntries[0][1])[0],
                            };
                        } catch (errorFormatting) {
                            console.debug(
                                errorFormatting,
                                "WorkflowRunForm::onExecute()",
                                "Invalid server error response format.",
                                errorData
                            );
                            this.$emit("submissionError", e);
                        }
                    } else {
                        this.$emit("submissionError", e);
                    }
                });
        },
        toArray(obj) {
            return obj ? Object.keys(obj).map((k) => obj[k]) : [];
        },
    },
};
</script>
