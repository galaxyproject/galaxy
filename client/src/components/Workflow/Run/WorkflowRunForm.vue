<template>
    <div>
        <div class="h4 clearfix mb-3">
            <b>Workflow: {{ model.name }}</b>
            <ButtonSpinner class="float-right" title="Run Workflow" id="run-workflow" @onClick="onExecute" />
        </div>
        <FormCard v-if="wpInputsAvailable" title="Workflow Parameters">
            <template v-slot:body>
                <Form :inputs="wpInputs" @onChange="onWpInputs" />
            </template>
        </FormCard>
        <FormCard title="History Options">
            <template v-slot:body>
                <Form :inputs="historyInputs" @onChange="onHistoryInputs" />
            </template>
        </FormCard>
        <FormCard v-if="cacheInputsAvailable" title="Job re-use Options">
            <template v-slot:body>
                <Form :inputs="cacheInputs" @onChange="onCacheInputs" />
            </template>
        </FormCard>
        <FormCard v-if="resourceInputsAvailable" title="Workflow Resource Options">
            <template v-slot:body>
                <Form :inputs="resourceInputs" @onChange="onResourceInputs" />
            </template>
        </FormCard>
        <div v-for="step in model.steps">
            <WorkflowRunToolStep
                v-if="step.step_type == 'tool'"
                :model="step"
                :step-data="stepData"
                :wp-data="wpData"
                @onChange="onToolStepInputs"
            />
            <WorkflowRunDefaultStep v-else :model="step" @onChange="onDefaultStepInputs" />
        </div>
    </div>
</template>

<script>
import { getGalaxyInstance } from "app";
import Form from "components/Form/Form";
import FormCard from "components/Form/FormCard";
import ButtonSpinner from "components/Common/ButtonSpinner";
import WorkflowRunDefaultStep from "./WorkflowRunDefaultStep";
import WorkflowRunToolStep from "./WorkflowRunToolStep";

export default {
    components: {
        Form,
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
            stepData: {},
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
        onExecute() {
            const Galaxy = getGalaxyInstance();
            const job_def = {
                new_history_name: this.historyData["new_history|name"] ? this.historyData["new_history|name"] : null,
                history_id: !this.historyData["new_history|name"] ? this.model.historyId : null,
                resource_params: this.resourceData,
                replacement_params: this.wpData,
                use_cached_job: this.cacheData["use_cached_job|check"] === "true",
                parameters: {},
                // Tool form will submit flat maps for each parameter
                // (e.g. "repeat_0|cond|param": "foo" instead of nested
                // data structures).
                parameters_normalized: true,
                // Tool form always wants a list of invocations back
                // so that inputs can be batched.
                batch: true,
            };
            var validated = true;
            /*for (var i in this.forms) {
                var form = this.forms[i];
                var job_inputs = form.data.create();
                var step = this.steps[i];
                var step_index = step.step_index;
                form.trigger("reset");
                for (var job_input_id in job_inputs) {
                    var input_value = job_inputs[job_input_id];
                    var input_id = form.data.match(job_input_id);
                    var input_def = form.input_list[input_id];
                    if (!input_def.step_linked) {
                        if (isDataStep(step)) {
                            validated = input_value && input_value.values && input_value.values.length > 0;
                            if (!validated && input_def.optional) {
                                validated = true;
                            }
                        } else {
                            validated =
                                input_def.optional ||
                                (input_def.is_workflow && input_value !== "") ||
                                (!input_def.is_workflow && input_value !== null);
                        }
                        if (!validated) {
                            if (input_def.type == "hidden") {
                                this.modal.show({
                                    title: _l("Workflow submission failed"),
                                    body: `Step ${step_index}: ${
                                        step.step_label || step.step_name
                                    } is in an invalid state. Please remove and re-add this step in the Workflow Editor.`,
                                    buttons: {
                                        Close: () => {
                                            this.modal.hide();
                                        },
                                    },
                                });
                            }
                            form.highlight(input_id);
                            break;
                        }
                        job_def.parameters[step_index] = job_def.parameters[step_index] || {};
                        job_def.parameters[step_index][job_input_id] = job_inputs[job_input_id];
                    }
                }
                if (!validated) {
                    break;
                }
            }
            if (!validated) {
                this._enabled(true);
                Galaxy.emit.debug("tool-form-composite::submit()", "Validation failed.", job_def);
            } else {
                Galaxy.emit.debug("tool-form-composite::submit()", "Validation complete.", job_def);
                invokeWorkflow(this.runWorkflowModel.workflowId, job_def)
                    .then((invocations) => {
                        Galaxy.emit.debug("tool-form-composite::submit", "Submission successful.", invocations);
                        if (Array.isArray(invocations) && invocations.length > 0) {
                            this.handleInvocations(invocations);
                        } else {
                            this.submissionErrorModal(job_def, invocations);
                        }
                        this._enabled(true);
                    })
                    .catch((response) => {
                        // TODO: Is this the same response as the Utils post would
                        // have had?
                        Galaxy.emit.debug("tool-form-composite::submit", "Submission failed.", response);
                        var input_found = false;
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
                            this.submissionErrorModal(job_def, response);
                        }
                        this._enabled(true);
                    });*/
        },
        handleInvocations(invocations) {
            this.$emit("submissionSuccess", invocations);
        },
        toArray(obj) {
            return obj ? Object.keys(obj).map((k) => obj[k]) : [];
        },
    },
};
</script>
