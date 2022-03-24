<template>
    <div>
        <div class="h4 clearfix mb-3">
            <b>Workflow: {{ model.name }}</b>
            <ButtonSpinner class="float-right" title="Run Workflow" id="run-workflow" @onClick="onExecute" />
        </div>
        <FormDisplay :inputs="formInputs" @onChange="onChange" />
        <!-- Options to default one way or the other, disable if admins want, etc.. -->
        <a href="#" @click="$emit('showAdvanced')">Expand to full workflow form.</a>
    </div>
</template>

<script>
import FormDisplay from "components/Form/FormDisplay";
import ButtonSpinner from "components/Common/ButtonSpinner";
import { invokeWorkflow } from "./services";
import { isWorkflowInput } from "components/Workflow/constants";
import { errorMessageAsString } from "utils/simple-error";

export default {
    components: {
        ButtonSpinner,
        FormDisplay,
    },
    props: {
        model: {
            type: Object,
            required: true,
        },
        targetHistory: {
            type: String,
            default: "current",
        },
        useJobCache: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            formData: {},
            inputTypes: {},
        };
    },
    computed: {
        formInputs() {
            const inputs = [];
            // Add workflow parameters.
            Object.values(this.model.wpInputs).forEach((input) => {
                const inputCopy = Object.assign({}, input);
                // do we want to keep the color if we're not showing steps?
                inputCopy.color = undefined;
                inputs.push(inputCopy);
                this.inputTypes[inputCopy.name] = "replacement_parameter";
            });
            // Add actual input modules.
            this.model.steps.forEach((step, i) => {
                if (!isWorkflowInput(step.step_type)) {
                    return;
                }
                const stepName = new String(step.step_index);
                const stepLabel = step.step_label || new String(step.step_index + 1);
                const help = step.annotation;
                const longFormInput = step.inputs[0];
                const stepAsInput = Object.assign({}, longFormInput, { name: stepName, help: help, label: stepLabel });
                // disable collection mapping...
                stepAsInput.flavor = "module";
                inputs.push(stepAsInput);
                this.inputTypes[stepName] = step.step_type;
            });
            return inputs;
        },
    },
    methods: {
        onChange(data) {
            this.formData = data;
        },
        onExecute() {
            const replacementParams = {};
            const inputs = {};
            for (const inputName in this.formData) {
                const value = this.formData[inputName];
                const inputType = this.inputTypes[inputName];
                if (inputType == "replacement_parameter") {
                    replacementParams[inputName] = value;
                } else if (isWorkflowInput(inputType)) {
                    inputs[inputName] = value;
                }
            }
            const data = {
                replacement_dict: replacementParams,
                inputs: inputs,
                inputs_by: "step_index",
                batch: true,
                use_cached_job: this.useJobCache,
                require_exact_tool_versions: false,
            };
            if (this.targetHistory == "current") {
                data.history_id = this.model.historyId;
            } else {
                data.new_history_name = this.model.name;
            }
            invokeWorkflow(this.model.workflowId, data)
                .then((invocations) => {
                    this.$emit("submissionSuccess", invocations);
                })
                .catch((error) => {
                    this.$emit("submissionError", errorMessageAsString(error));
                });
        },
    },
};
</script>
