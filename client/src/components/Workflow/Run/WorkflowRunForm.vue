<template>
    <div>
        <div class="h4 clearfix mb-3">
            <b>Workflow: {{ model.name }}</b>
            <ButtonSpinner
                id="run-workflow"
                class="float-right"
                title="Run Workflow"
                :wait="showExecuting"
                @onClick="onExecute"
            />
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
        <FormCard v-if="cacheInputsAvailable" title="Job re-use Options">
            <template v-slot:body>
                <FormDisplay :inputs="cacheInputs" @onChange="onCacheInputs" />
            </template>
        </FormCard>
        <FormCard v-if="resourceInputsAvailable" title="Workflow Resource Options">
            <template v-slot:body>
                <FormDisplay :inputs="resourceInputs" @onChange="onResourceInputs" />
            </template>
        </FormCard>
        <div v-for="step in model.steps">
            <WorkflowRunToolStep
                v-if="step.step_type == 'tool'"
                :model="step"
                :step-data="stepData"
                :validation-scroll-to="getValidationScrollTo(step.index)"
                :wp-data="wpData"
                @onChange="onToolStepInputs"
                @onValidation="onValidation"
            />
            <WorkflowRunDefaultStep
                v-else
                :model="step"
                :validation-scroll-to="getValidationScrollTo(step.index)"
                @onChange="onDefaultStepInputs"
                @onValidation="onValidation"
            />
        </div>
    </div>
</template>

<script>
import { getGalaxyInstance } from "app";
import FormDisplay from "components/Form/FormDisplay";
import FormCard from "components/Form/FormCard";
import ButtonSpinner from "components/Common/ButtonSpinner";
import WorkflowRunDefaultStep from "./WorkflowRunDefaultStep";
import WorkflowRunToolStep from "./WorkflowRunToolStep";
import { invokeWorkflow } from "./services";

export default {
    components: {
        FormDisplay,
        FormCard,
        ButtonSpinner,
        WorkflowRunDefaultStep,
        WorkflowRunToolStep,
    },
    props: {
        model: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            showExecuting: false,
            stepData: {},
            stepValidations: {},
            stepScrollTo: {},
            wpData: {},
            historyData: {},
            cacheData: {},
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
                    ],
                },
            ],
        };
    },
    computed: {
        cacheInputsAvailable() {
            const Galaxy = getGalaxyInstance();
            var extra_user_preferences = {};
            if (Galaxy.user.attributes.preferences && "extra_user_preferences" in Galaxy.user.attributes.preferences) {
                extra_user_preferences = JSON.parse(Galaxy.user.attributes.preferences.extra_user_preferences);
            }
            return;
            "use_cached_job|use_cached_job_checkbox" in extra_user_preferences
                ? extra_user_preferences["use_cached_job|use_cached_job_checkbox"] === "true"
                : false;
        },
        cacheInputs() {
            return [
                {
                    type: "conditional",
                    name: "use_cached_job",
                    test_param: {
                        name: "check",
                        label: "Attempt to reuse jobs with identical parameters?",
                        type: "boolean",
                        value: "false",
                        help: "This may skip executing jobs that you have already run.",
                    },
                },
            ];
        },
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
    },
    methods: {
        getValidationScrollTo(stepId) {
            if (this.stepScrollTo.stepId == stepId) {
                return this.stepScrollTo.stepError;
            }
            return [];
        },
        onDefaultStepInputs(stepId, data) {
            this.stepData[stepId] = data;
            this.stepData = Object.assign({}, this.stepData);
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
        onCacheInputs(data) {
            this.cacheData = data;
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

            const jobDef = {
                new_history_name: this.historyData["new_history|name"] ? this.historyData["new_history|name"] : null,
                history_id: !this.historyData["new_history|name"] ? this.model.historyId : null,
                resource_params: this.resourceData,
                replacement_params: this.wpData,
                use_cached_job: this.cacheData["use_cached_job|check"] === "true",
                parameters: this.stepData,
                // Tool form will submit flat maps for each parameter
                // (e.g. "repeat_0|cond|param": "foo" instead of nested
                // data structures).
                parameters_normalized: true,
                // Tool form always wants a list of invocations back
                // so that inputs can be batched.
                batch: true,
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
                        } catch (e) {
                            console.debug(
                                e,
                                "WorkflowRunForm::onExecute()",
                                "Invalid server error response.",
                                errorData
                            );
                            this.$emit("submissionError", response);
                        }
                    } else {
                        this.$emit("submissionError", response);
                    }
                });
        },
        toArray(obj) {
            return obj ? Object.keys(obj).map((k) => obj[k]) : [];
        },
    },
};
</script>
