<template>
    <div>
        <div class="h4 clearfix mb-3">
            <b>Workflow: {{ model.name }}</b>
            <ButtonSpinner
                id="run-workflow"
                class="float-right"
                title="Run Workflow"
                :wait="disableExecution"
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
                :step-scroll-to="stepScrollTo"
                :wp-data="wpData"
                @onChange="onToolStepInputs"
                @onValidation="onValidation"
            />
            <WorkflowRunDefaultStep
                v-else
                :model="step"
                :step-scroll-to="stepScrollTo"
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
            disableExecution: false,
            stepData: {},
            stepValidation: {},
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
            this.stepValidation[stepId] = validation;
        },
        onExecute() {
            for (const [stepId, stepValidation] of Object.entries(this.stepValidation)) {
                if (stepValidation) {
                    const validation = stepValidation.slice();
                    this.stepScrollTo = {
                        stepId,
                        validation,
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
            this.disableExecution = true;
            invokeWorkflow(this.model.workflowId, jobDef)
                .then((invocations) => {
                    console.debug("WorkflowRunForm::onExecute()", "Submission successful.", invocations);
                    this.disableExecution = false;
                    this.$emit("submissionSuccess", invocations);
                })
                .catch((response) => {
                    // TODO: Is this the same response as the Utils post would
                    // have had?
                    console.debug("WorkflowRunForm::onExecute()", "Submission failed.", response);
                    /*var input_found = false;
                    if (response && response.err_data) {
                        for (var i in this.forms) {
                            var form = this.forms[i];
                            var step_related_errors = response.err_data[form.model.get("step_index")];
                            if (step_related_errors) {
                                var error_messages = form.data.matchResponse(step_related_errors);
                                for (var input_id in error_messages) {
                                    form.highlight(input_id, error_messages[input_id]);
                                    input_found = true;
                                    break;
                                }
                            }
                        }
                    }
                    if (!input_found) {
                        this.submissionErrorModal(jobDef, response);
                    }*/
                    this.$emit("submissionError", response);
                    this.disableExecution = false;
                });
        },
        toArray(obj) {
            return obj ? Object.keys(obj).map((k) => obj[k]) : [];
        },
    },
};
</script>
